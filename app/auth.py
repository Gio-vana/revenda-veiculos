from collections.abc import Callable
from dataclasses import dataclass
from typing import Annotated, Any

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

bearer = HTTPBearer(auto_error=False, description="Token obtido no serviço de identidade (/identidade/auth/login)")


@dataclass(frozen=True)
class Usuario:
    id: str
    papel: str


class VerificadorToken:
    def __init__(self, obter_chave: Callable[[str], Any], issuer: str, audience: str) -> None:
        self._obter_chave = obter_chave
        self._issuer = issuer
        self._audience = audience

    @classmethod
    def por_jwks(cls, jwks_url: str, issuer: str, audience: str) -> "VerificadorToken":
        cliente = jwt.PyJWKClient(jwks_url, cache_keys=True, lifespan=300, timeout=5)
        return cls(lambda token: cliente.get_signing_key_from_jwt(token).key, issuer, audience)

    def verificar(self, token: str) -> Usuario:
        chave = self._obter_chave(token)
        claims = jwt.decode(
            token,
            chave,
            algorithms=["RS256"],
            issuer=self._issuer,
            audience=self._audience,
            options={"require": ["exp", "iss", "aud", "sub"]},
            leeway=30,  # tolera pequenas diferenças de relógio entre os servidores
        )
        return Usuario(id=claims["sub"], papel=claims.get("papel", ""))


def usuario_autenticado(
    request: Request,
    credenciais: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
) -> Usuario:
    if credenciais is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token ausente", {"WWW-Authenticate": "Bearer"})
    try:
        return request.app.state.verificador.verificar(credenciais.credentials)
    except (jwt.InvalidTokenError, jwt.PyJWKClientError) as erro:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token inválido", {"WWW-Authenticate": "Bearer"}) from erro


def exigir_papel(papel: str) -> Callable[[Usuario], Usuario]:
    def dependencia(usuario: Annotated[Usuario, Depends(usuario_autenticado)]) -> Usuario:
        if usuario.papel != papel:
            raise HTTPException(status.HTTP_403_FORBIDDEN, f"Acesso permitido apenas ao papel '{papel}'")
        return usuario

    return dependencia


UsuarioAutenticado = Annotated[Usuario, Depends(usuario_autenticado)]
Gestor = Annotated[Usuario, Depends(exigir_papel("gestor"))]
Cliente = Annotated[Usuario, Depends(exigir_papel("cliente"))]
