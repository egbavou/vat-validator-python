<?php

declare(strict_types=1);

use Egbavou\VatValidator\CheckStatus;
use Egbavou\VatValidator\Internal\ViesException;
use Egbavou\VatValidator\InvalidIdentifierException;
use Egbavou\VatValidator\UnavailableReason;
use Egbavou\VatValidator\VatNumber;
use Egbavou\VatValidator\VatNumberChecker;
use GuzzleHttp\Psr7\HttpFactory;
use GuzzleHttp\Psr7\Response;
use Illuminate\Support\Env;
use Psr\Http\Client\ClientInterface;
use Psr\Http\Message\RequestInterface;
use Psr\Http\Message\ResponseInterface;

$directory = getenv('VAT_VALIDATOR_PHP_DIR') ?: __DIR__.'/../../../vat-validator';
require $directory.'/vendor/autoload.php';
Env::disablePutenv();

function decoded(?string $value): ?string
{
    return $value === null ? null : base64_decode($value, true);
}

final class OracleClient implements ClientInterface
{
    public array $requests = [];

    public function __construct(private array $case) {}

    public function sendRequest(RequestInterface $request): ResponseInterface
    {
        $this->requests[] = [
            'method' => $request->getMethod(),
            'url' => (string) $request->getUri(),
            'body' => (string) $request->getBody(),
            'Content-Type' => $request->getHeaderLine('Content-Type'),
            'Accept' => $request->getHeaderLine('Accept'),
        ];
        if ($this->case['throw'] ?? false) {
            throw new RuntimeException('injected');
        }
        return new Response($this->case['status'] ?? 200, [], base64_decode($this->case['body'], true));
    }
}

function project(array $case, string $directory): array
{
    if ($case['op'] === 'settings') {
        foreach (['VAT_VALIDATOR_VIES_TIMEOUT', 'VAT_VALIDATOR_REQUESTER'] as $key) {
            unset($_SERVER[$key], $_ENV[$key]);
        }
        foreach ($case['env'] as $key => $value) {
            $_SERVER[$key] = $_ENV[$key] = decoded($value);
        }
        $config = require $directory.'/config/vat-validator.php';
        $timeout = $config['vies']['timeout'];
        $requester = $config['vies']['requester'];
        // Copied verbatim from VatValidatorServiceProvider::register().
        return [
            'timeout' => is_numeric($timeout) && (float) $timeout > 0 ? (float) $timeout : 20.0,
            'requester' => is_string($requester) && trim($requester) !== '' ? $requester : null,
        ];
    }
    if ($case['op'] === 'parse' || $case['op'] === 'from_siren') {
        try {
            $number = $case['op'] === 'from_siren'
                ? VatNumber::fromSiren(decoded($case['input']))
                : VatNumber::from(decoded($case['input']), decoded($case['country'] ?? null));
        } catch (InvalidIdentifierException $error) {
            return ['reason' => $error->reason->value];
        }
        return ['value' => $number->value, 'prefix' => $number->prefix,
            'number' => $number->number, 'country_code' => $number->countryCode];
    }
    $client = new OracleClient($case);
    $factory = new HttpFactory;
    $checker = new VatNumberChecker($client, $factory, $factory, requester: decoded($case['requester'] ?? null));
    $result = $checker->check(decoded($case['input']), decoded($case['country'] ?? null));
    $failure = null;
    if ($result->failure instanceof ViesException) {
        $failure = ['kind' => 'ViesError', 'message' => $result->failure->getMessage()];
    } elseif ($result->failure !== null) {
        $failure = ['kind' => 'original'];
        if (($case['throw'] ?? false) || (
            $result->unavailableReason === UnavailableReason::InvalidJson
            && $result->failure instanceof JsonException
            && in_array($result->failure->getMessage(), [
                'Maximum stack depth exceeded',
                'Single unpaired UTF-16 surrogate in unicode escape',
            ], true)
        )) {
            $failure['message'] = $result->failure->getMessage();
        }
    }
    return [
        'status' => $result->status->value,
        'vat_number' => $result->vatNumber?->value,
        'name' => $result->name, 'address' => $result->address, 'reference' => $result->reference,
        'unavailable_reason' => $result->unavailableReason?->value,
        'registry_error_code' => $result->registryErrorCode,
        'checked_at' => in_array($result->status, [CheckStatus::Found, CheckStatus::NotFound], true)
            ? $result->checkedAt->format('Y-m-d\TH:i:s.v\Z') : null,
        'failure' => $failure, 'requests' => $client->requests,
    ];
}

while (($line = fgets(STDIN)) !== false) {
    $case = json_decode($line, true, 512, JSON_THROW_ON_ERROR);
    echo json_encode(project($case, $directory), JSON_THROW_ON_ERROR), "\n";
}
