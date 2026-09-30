# OPC UA Security

## Core model

FiltersReporting v1.0 uses:

> one filter = one independent machine / OPC UA server

## Per-machine settings

Each machine can define:

- endpoint
- Security Policy
- Security Mode
- Application URI
- client certificate
- private key
- trusted certificate directory
- expected server certificate
- server certificate validation
- authentication mode
- username/password
- connection/request timeouts
- reconnect delay
- NodeIds

## Security Policies

```text
None
Basic256Sha256
Aes128Sha256RsaOaep
Aes256Sha256RsaPss
```

## Security Modes

```text
None
Sign
SignAndEncrypt
```

## Authentication

Client-side:

```text
Anonymous
Username/Password
```

Per-machine passwords are protected with Windows DPAPI.

## Local OPC UA Server

The optional embedded server exposes selected monitoring data as read-only variables.

The current v1.0 runtime server uses:

```text
AnonymousIdentityToken
```

Server-side Username/Password is not advertised as an active v1.0 runtime feature.
