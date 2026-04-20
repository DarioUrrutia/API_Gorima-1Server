<?php
/**
 * Wrapper REST minimal sobre el webservice nativo de vTiger.
 *
 * Rutas:
 *   GET    /api/{Module}                   → lista (params: q, limit, offset, fields)
 *   GET    /api/{Module}/describe          → campos del modulo
 *   GET    /api/{Module}/{id}              → lee un registro
 *   POST   /api/{Module}                   → crea (body JSON)
 *   PUT    /api/{Module}/{id}              → actualiza parcial (body JSON)
 *   DELETE /api/{Module}/{id}              → borra
 *   POST   /api/{Module}/{id}/comments     → añade ModComments relacionado
 *
 * Auth:
 *   Header "Authorization: Bearer <API_TOKEN>"  (o "X-API-Token: <API_TOKEN>")
 */

declare(strict_types=1);

// ───────────────────────── bootstrap ─────────────────────────

header('Content-Type: application/json; charset=utf-8');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET, POST, PUT, DELETE, OPTIONS');
header('Access-Control-Allow-Headers: Authorization, Content-Type, X-API-Token');

if (($_SERVER['REQUEST_METHOD'] ?? '') === 'OPTIONS') { http_response_code(204); exit; }

$configPath = __DIR__ . '/config.php';
if (!is_file($configPath)) {
    respond(500, ['error' => 'config_missing', 'message' => 'config.php no existe']);
}
$CONFIG = require $configPath;

// ───────────────────────── auth ─────────────────────────

$provided = extractBearer();
if ($provided === null || !hash_equals((string)$CONFIG['api_token'], $provided)) {
    respond(401, ['error' => 'unauthorized', 'message' => 'Token invalido o ausente']);
}

// ───────────────────────── routing ─────────────────────────

$path = trim((string)($_SERVER['PATH_INFO'] ?? ''), '/');
if ($path === '') $path = trim((string)($_GET['_path'] ?? ''), '/');
$method = strtoupper($_SERVER['REQUEST_METHOD'] ?? 'GET');
$segments = $path === '' ? [] : explode('/', $path);

try {
    $vt = new VtigerClient($CONFIG);
    $response = route($method, $segments, $vt, $CONFIG);
    respond(200, $response);
} catch (ApiException $e) {
    respond($e->httpStatus, ['error' => $e->errorCode, 'message' => $e->getMessage(), 'details' => $e->details]);
} catch (Throwable $e) {
    $payload = ['error' => 'internal_error', 'message' => $e->getMessage()];
    if (!empty($CONFIG['debug'])) $payload['trace'] = $e->getTraceAsString();
    respond(500, $payload);
}

// ───────────────────────── router ─────────────────────────

function route(string $method, array $seg, VtigerClient $vt, array $config): array
{
    if (count($seg) === 0) {
        return ['ok' => true, 'service' => 'vtiger-rest-wrapper', 'version' => '1.0.0'];
    }

    $module = $seg[0] ?? '';
    if (!in_array($module, $config['allowed_modules'], true)) {
        throw new ApiException('module_not_allowed', "Modulo '$module' no permitido", 403);
    }

    // /{Module}
    if (count($seg) === 1) {
        if ($method === 'GET')  return $vt->listRecords($module, $_GET);
        if ($method === 'POST') return $vt->create($module, readJsonBody());
        throw new ApiException('method_not_allowed', "Metodo $method no soportado en /$module", 405);
    }

    // /{Module}/describe
    if (count($seg) === 2 && $seg[1] === 'describe' && $method === 'GET') {
        return $vt->describe($module);
    }

    // /{Module}/{id}
    if (count($seg) === 2) {
        $id = $seg[1];
        if ($method === 'GET')    return $vt->retrieve($module, $id);
        if ($method === 'PUT')    return $vt->update($module, $id, readJsonBody());
        if ($method === 'DELETE') return $vt->delete($module, $id);
        throw new ApiException('method_not_allowed', "Metodo $method no soportado en /$module/$id", 405);
    }

    // /{Module}/{id}/comments
    if (count($seg) === 3 && $seg[2] === 'comments' && $method === 'POST') {
        $id = $seg[1];
        $body = readJsonBody();
        $text = trim((string)($body['content'] ?? $body['commentcontent'] ?? ''));
        if ($text === '') throw new ApiException('bad_request', "Falta campo 'content' con el texto del comentario", 400);
        return $vt->addComment($module, $id, $text, $body['assigned_user_id'] ?? null);
    }

    throw new ApiException('not_found', "Ruta no encontrada: /$method /" . implode('/', $seg), 404);
}

// ───────────────────────── Vtiger client ─────────────────────────

class VtigerClient
{
    private string $url;
    private string $user;
    private string $accessKey;
    private int $timeout;
    private ?string $sessionName = null;
    private ?string $userId = null;
    private array $modulePrefixCache = [];

    public function __construct(array $config)
    {
        $this->url = $config['vtiger_ws_url'];
        $this->user = $config['vtiger_user'];
        $this->accessKey = $config['vtiger_access_key'];
        $this->timeout = (int)($config['vtiger_ws_timeout'] ?? 30);
    }

    private function login(): void
    {
        if ($this->sessionName !== null) return;

        $chal = $this->wsGet(['operation' => 'getchallenge', 'username' => $this->user]);
        $challengeToken = $chal['token'] ?? null;
        if (!$challengeToken) throw new ApiException('vtiger_login_failed', 'No se pudo obtener challenge token', 502, $chal);

        $login = $this->wsPost([
            'operation' => 'login',
            'username'  => $this->user,
            'accessKey' => md5($challengeToken . $this->accessKey),
        ]);
        if (empty($login['sessionName'])) throw new ApiException('vtiger_login_failed', 'Login al webservice fallo', 502, $login);

        $this->sessionName = $login['sessionName'];
        $this->userId = $login['userId'] ?? null;
    }

    public function describe(string $module): array
    {
        $this->login();
        return $this->wsGet(['operation' => 'describe', 'sessionName' => $this->sessionName, 'elementType' => $module]);
    }

    private function modulePrefix(string $module): string
    {
        if (!isset($this->modulePrefixCache[$module])) {
            $d = $this->describe($module);
            $this->modulePrefixCache[$module] = (string)($d['idPrefix'] ?? '');
        }
        return $this->modulePrefixCache[$module];
    }

    private function toWsId(string $module, string $id): string
    {
        if (str_contains($id, 'x')) return $id;
        $prefix = $this->modulePrefix($module);
        if ($prefix === '') throw new ApiException('unknown_module_prefix', "No se pudo resolver idPrefix de $module", 500);
        return $prefix . 'x' . $id;
    }

    public function retrieve(string $module, string $id): array
    {
        $this->login();
        $wsId = $this->toWsId($module, $id);
        return $this->wsGet(['operation' => 'retrieve', 'sessionName' => $this->sessionName, 'id' => $wsId]);
    }

    public function listRecords(string $module, array $query): array
    {
        $this->login();
        $limit  = max(1, min(200, (int)($query['limit']  ?? 50)));
        $offset = max(0, (int)($query['offset'] ?? 0));
        $userFields = isset($query['fields']) ? preg_replace('/[^a-zA-Z0-9_,]/', '', (string)$query['fields']) : '*';
        $fields = $userFields; // SELECT final — se extenderá con search fields abajo si hace falta
        $q      = $query['q'] ?? '';

        $vtqlWhere = '';
        if ($q !== '') {
            // Busqueda simple contra campos textuales principales.
            // Campos donde el parametro ?q= buscara con LIKE.
            // Pensado para que el agente (LLM) pueda encontrar registros por palabras clave
            // del lenguaje natural: nombre, telefono, IVA, strada, localita, descripcion, etc.
            $fieldMap = [
                'Accounts'    => ['accountname', 'email1', 'phone', 'cf_1107', 'cf_1105', 'cf_1103', 'cf_1111', 'cf_1125'],
                'Contacts'    => ['firstname', 'lastname', 'email', 'phone'],
                'Potentials'  => ['potentialname', 'potential_no', 'description', 'cf_919', 'cf_925', 'cf_895', 'cf_897', 'cf_891', 'cf_859', 'cf_969', 'cf_915', 'cf_913', 'cf_1009'],
                'Events'      => ['subject', 'location', 'description'],
                'Calendar'    => ['subject', 'location', 'description'],
                'ModComments' => ['commentcontent'],
            ];
            $cands = $fieldMap[$module] ?? ['*'];
            // Tokeniza q por espacios. VTQL no soporta paréntesis, así que armamos
            // un OR plano con todos (token × variant × field) como WHERE para traer
            // un superconjunto, y luego filtramos en PHP (más abajo) exigiendo que
            // cada token aparezca en algún campo del record (AND entre tokens).
            // Para cada token generamos variantes si hay frontera letra-dígito
            // (ej "SS106" -> también "SS 106"), así el CRM italiano donde se escribe
            // "SS 106" con espacio matchea cuando el LLM pasa "SS106" pegado.
            $variants = function (string $tok): array {
                $v = [$tok];
                if (preg_match('/^(\p{L}+)(\d.+)$/u', $tok, $m)) $v[] = $m[1] . ' ' . $m[2];
                if (preg_match('/^(\d+)(\p{L}.+)$/u', $tok, $m)) $v[] = $m[1] . ' ' . $m[2];
                return array_values(array_unique($v));
            };
            $tokens = preg_split('/\s+/', trim((string)$q)) ?: [];
            // Stopwords italianas/inglesas/frases conversacionales: el agente LLM
            // suele mandar "cerca opportunità SS106" en vez de "SS106"; limpiamos
            // esas palabras para que queden solo los keywords reales.
            $stop = [
                'a','al','alla','allo','ai','agli','alle','da','dal','dalla','dallo','dai','dagli','dalle',
                'di','del','della','dello','dei','degli','delle','in','nel','nella','nello','nei','negli','nelle',
                'su','sul','sulla','sullo','sui','sugli','sulle','per','con','e','o','ed','od','ma','se',
                'il','lo','la','i','gli','le','un','uno','una','che','cui','dove','quando','come',
                'cerca','cercare','trova','trovare','mostra','mostrami','dammi','voglio','vorrei','ho','bisogno',
                'opportunita','opportunità','opportunity','opportunities','potential','potentials',
                'azienda','aziende','account','accounts','contatto','contatti','contact','contacts',
                'evento','eventi','event','events','commento','commenti','comment','comments',
                'zona','regione','localita','località','strada','via',
                'the','of','and','or','for','with','in','on','at','by','a','an','is','are','was','were','be','to','find','search','show','get','list','about','near',
            ];
            $tokens = array_values(array_filter(
                array_map(fn($t) => trim((string)$t), $tokens),
                fn($t) => $t !== '' && mb_strlen($t) >= 2 && !in_array(mb_strtolower($t), $stop, true)
            ));
            $orParts = [];
            foreach ($tokens as $tok) {
                foreach ($variants($tok) as $var) {
                    $escaped = str_replace(["'", '%'], ["\\'", '\\%'], $var);
                    foreach ($cands as $f) {
                        if ($f === '*') continue;
                        $orParts[] = "$f LIKE '%$escaped%'";
                    }
                }
            }
            if ($orParts) $vtqlWhere = ' WHERE ' . implode(' OR ', $orParts);

            // Si el usuario pidió campos específicos, aseguramos incluir los
            // search fields en el SELECT para que el post-filter PHP funcione.
            // Luego abajo filtramos el output para devolver solo lo pedido.
            if ($userFields !== '*') {
                $userList = array_filter(array_map('trim', explode(',', $userFields)));
                $needed = array_unique(array_merge($userList, array_filter($cands, fn($f) => $f !== '*')));
                $fields = implode(',', $needed);
            }
        }

        // Con multi-token pedimos más candidatos (el OR plano amplía el superconjunto)
        // y luego filtramos abajo para dejar solo los que contienen TODOS los tokens.
        $queryLimit  = (isset($tokens) && count($tokens) > 1) ? min(200, $limit * 5) : $limit;
        $queryOffset = (isset($tokens) && count($tokens) > 1) ? 0 : $offset;
        $vtql = "SELECT $fields FROM $module" . $vtqlWhere . " LIMIT $queryOffset, $queryLimit;";
        $result = $this->wsGet(['operation' => 'query', 'sessionName' => $this->sessionName, 'query' => $vtql]);
        if (!is_array($result)) $result = [];

        if (isset($tokens) && count($tokens) > 0) {
            $result = array_values(array_filter($result, function ($row) use ($tokens, $cands, $variants) {
                $hay = '';
                foreach ($cands as $f) {
                    if ($f === '*') continue;
                    if (isset($row[$f])) $hay .= ' ' . $row[$f];
                }
                $hayLower = mb_strtolower($hay);
                foreach ($tokens as $tok) {
                    $matched = false;
                    foreach ($variants($tok) as $var) {
                        if (mb_strpos($hayLower, mb_strtolower($var)) !== false) { $matched = true; break; }
                    }
                    if (!$matched) return false;
                }
                return true;
            }));
            $result = array_slice($result, $offset, $limit);
        }

        // Si el usuario pidió campos específicos, trimamos el output a solo esos
        // (internamente habíamos añadido los search fields para el post-filter).
        if ($userFields !== '*') {
            $keep = array_filter(array_map('trim', explode(',', $userFields)));
            $keepSet = array_flip($keep);
            $result = array_map(function ($row) use ($keepSet) {
                return array_intersect_key($row, $keepSet);
            }, $result);
        }
        return ['module' => $module, 'count' => count($result), 'items' => $result];
    }

    public function create(string $module, array $data): array
    {
        $this->login();
        return $this->wsPost([
            'operation'   => 'create',
            'sessionName' => $this->sessionName,
            'elementType' => $module,
            'element'     => json_encode($data),
        ]);
    }

    public function update(string $module, string $id, array $data): array
    {
        $this->login();
        $data['id'] = $this->toWsId($module, $id);
        return $this->wsPost([
            'operation'   => 'revise',
            'sessionName' => $this->sessionName,
            'element'     => json_encode($data),
        ]);
    }

    public function delete(string $module, string $id): array
    {
        $this->login();
        $wsId = $this->toWsId($module, $id);
        $result = $this->wsPost([
            'operation'   => 'delete',
            'sessionName' => $this->sessionName,
            'id'          => $wsId,
        ]);
        return ['deleted' => true, 'id' => $wsId, 'result' => $result];
    }

    public function addComment(string $relatedModule, string $relatedId, string $content, ?string $assignedUserId = null): array
    {
        $this->login();
        $relatedWsId = $this->toWsId($relatedModule, $relatedId);
        $element = [
            'commentcontent'   => $content,
            'related_to'       => $relatedWsId,
            'assigned_user_id' => $assignedUserId ?: ($this->userId ?? ''),
        ];
        return $this->wsPost([
            'operation'   => 'create',
            'sessionName' => $this->sessionName,
            'elementType' => 'ModComments',
            'element'     => json_encode($element),
        ]);
    }

    // ── HTTP helpers ──

    private function wsGet(array $params): array
    {
        $url = $this->url . '?' . http_build_query($params);
        return $this->httpCall('GET', $url, null);
    }

    private function wsPost(array $params): array
    {
        return $this->httpCall('POST', $this->url, http_build_query($params));
    }

    private function httpCall(string $method, string $url, ?string $body): array
    {
        $ch = curl_init($url);
        curl_setopt_array($ch, [
            CURLOPT_CUSTOMREQUEST  => $method,
            CURLOPT_RETURNTRANSFER => true,
            CURLOPT_TIMEOUT        => $this->timeout,
            CURLOPT_CONNECTTIMEOUT => 10,
        ]);
        if ($body !== null) {
            curl_setopt($ch, CURLOPT_POSTFIELDS, $body);
            curl_setopt($ch, CURLOPT_HTTPHEADER, ['Content-Type: application/x-www-form-urlencoded']);
        }
        $raw = curl_exec($ch);
        if ($raw === false) {
            $err = curl_error($ch);
            curl_close($ch);
            throw new ApiException('vtiger_ws_unreachable', "Fallo llamada al webservice: $err", 502);
        }
        $code = curl_getinfo($ch, CURLINFO_HTTP_CODE);
        curl_close($ch);

        $decoded = json_decode((string)$raw, true);
        if (!is_array($decoded)) {
            throw new ApiException('vtiger_ws_bad_response', "Respuesta no-JSON del webservice", 502, ['http_code' => $code, 'raw' => substr((string)$raw, 0, 500)]);
        }
        if (($decoded['success'] ?? false) !== true) {
            $err = $decoded['error'] ?? [];
            throw new ApiException('vtiger_ws_error', (string)($err['message'] ?? 'Error del webservice'), 502, $decoded);
        }
        return $decoded['result'] ?? [];
    }
}

// ───────────────────────── utils ─────────────────────────

class ApiException extends Exception
{
    public function __construct(public string $errorCode, string $message, public int $httpStatus = 400, public mixed $details = null)
    {
        parent::__construct($message);
    }
}

function respond(int $status, array $data): void
{
    http_response_code($status);
    echo json_encode($data, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
    exit;
}

function extractBearer(): ?string
{
    $hdrs = function_exists('getallheaders') ? getallheaders() : [];
    $h = $hdrs['Authorization'] ?? $hdrs['authorization']
        ?? ($_SERVER['HTTP_AUTHORIZATION'] ?? $_SERVER['REDIRECT_HTTP_AUTHORIZATION'] ?? '');
    if (is_string($h) && preg_match('/Bearer\s+(.+)/i', $h, $m)) return trim($m[1]);

    $x = $hdrs['X-API-Token'] ?? $hdrs['x-api-token'] ?? ($_SERVER['HTTP_X_API_TOKEN'] ?? '');
    if (is_string($x) && $x !== '') return trim($x);

    return null;
}

function readJsonBody(): array
{
    $raw = file_get_contents('php://input');
    if ($raw === false || $raw === '') return [];
    $data = json_decode($raw, true);
    if (!is_array($data)) throw new ApiException('invalid_json', 'Body no es JSON valido', 400);
    return $data;
}
