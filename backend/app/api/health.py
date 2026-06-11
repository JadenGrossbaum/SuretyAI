from fastapi import APIRouter

router = APIRouter(tags=['health'])


@router.get('/')
def root() -> dict[str, object]:
    return {
        'message': 'Welcome to SuretyAI. Visit /docs to explore the local API.',
        'links': {'docs': '/docs', 'health': '/health'},
    }


@router.get('/health')
def health_check() -> dict[str, str]:
    return {'status': 'ok'}
