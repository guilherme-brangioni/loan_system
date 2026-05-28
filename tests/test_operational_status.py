def test_admin_can_access_operational_status(
    client,
    login_user,
):
    login_user(
        email="admin.status@teste.com",
        role="ADMIN",
    )

    response = client.get(
        "/status-operacional/",
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert "Status operacional".encode("utf-8") in response.data


def test_operator_cannot_access_operational_status(
    client,
    login_user,
):
    login_user(
        email="operador.status@teste.com",
        role="OPERADOR",
    )

    response = client.get(
        "/status-operacional/",
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert "Acesso restrito ao administrador".encode("utf-8") in response.data