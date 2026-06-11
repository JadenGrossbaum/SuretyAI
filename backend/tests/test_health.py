def test_health_check(client):
    response = client.get('/health')

    assert response.status_code == 200
    assert response.json() == {'status': 'ok'}


def test_root_route_links_to_docs(client):
    response = client.get('/')

    assert response.status_code == 200
    assert response.json() == {
        'message': 'Welcome to SuretyAI. Visit /docs to explore the local API.',
        'links': {'docs': '/docs', 'health': '/health'},
    }
