# ADR-001: Serviço de identidade próprio, em repositório separado

**Status:** Aceita

## Contexto

O enunciado exige que o registro e a autorização de compradores fiquem **totalmente apartados** do resto da solução, para separar dados de clientes dos dados transacionais de vendas. Permite Auth0, Cognito, Keycloak ou implementação própria.

## Decisão

Implementar um **serviço de identidade próprio em FastAPI** (`revenda-identidade`), com repositório, banco PostgreSQL, pipeline de CI/CD e deploy próprios. Ele cadastra compradores, autentica e emite **JWT assinado com RS256**, publicando a chave pública em `/.well-known/jwks.json`. A API da revenda valida os tokens só com a chave pública e guarda apenas o `sub`.

## Alternativas consideradas

| Alternativa | Por que não |
|---|---|
| Keycloak | Muito completo, mas pesado (Java, ~500 MB de RAM) para a VM pequena; quase todo o trabalho seria configuração, não código |
| AWS Cognito / Auth0 | Dependência de serviço externo e de conta/configuração adicional; dificulta rodar tudo localmente |
| Módulo de usuários dentro da revenda | Viola o requisito de separação |

## Consequências

- Separação física comprovável: outro repositório, outro banco, outra rede Docker; a revenda não tem credencial nem rota de rede para o banco de identidade.
- Dados pessoais (nome, e-mail, CPF, telefone, hash da senha) existem só na identidade (LGPD, princípio da necessidade).
- Contrato simples e padrão de mercado (JWT + JWKS): trocar por Keycloak ou Cognito no futuro exige só mudar `JWKS_URL`, `JWT_ISSUER` e o claim de papel.
- Responsabilidade de segurança é nossa: uso de bibliotecas consolidadas (bcrypt, PyJWT/cryptography), sem criptografia caseira. Recursos como recuperação de senha, MFA e refresh token ficam como evolução.
