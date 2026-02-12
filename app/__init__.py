from fastapi import FastAPI
from app.api.router import api_router
from app.core.exception_handlers import register_exception_handlers
from app.core.middlewares import register_middleware


version = "v1"

description = """
A REST API for a account service.
    """

version_prefix =f"/api/{version}"

app = FastAPI(
    title="aurashi-travishta-catalog-service",
    description=description,
    version=version,
    license_info={"name": "MIT License", "url": "https://opensource.org/license/mit"},
    terms_of_service="httpS://example.com/tos",
    openapi_url=f"{version_prefix}/openapi.json",
    docs_url=f"{version_prefix}/docs",
    redoc_url=f"{version_prefix}/redoc"
)

register_exception_handlers(app)


register_middleware(app)


app.include_router(api_router, prefix=f"{version_prefix}")