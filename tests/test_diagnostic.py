from services.diagnostic_service import DiagnosticService


def test_admin_can_access_diagnostic_page(client, login_user):
    """
    ADMIN pode acessar diagnóstico.
    """

    login_user(
        email="admin.diagnostic@teste.com",
        role="ADMIN",
    )

    response = client.get(
        "/diagnostico/",
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert "Diagnóstico do sistema".encode("utf-8") in response.data


def test_operator_cannot_access_diagnostic_page(client, login_user):
    """
    OPERADOR não pode acessar diagnóstico.
    """

    login_user(
        email="operador.diagnostic@teste.com",
        role="OPERADOR",
    )

    response = client.get(
        "/diagnostico/",
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert "Acesso restrito ao administrador".encode("utf-8") in response.data


def test_diagnostic_service_returns_checks(app, login_user):
    """
    Serviço de diagnóstico deve retornar uma lista de verificações.
    """

    login_user(role="ADMIN")

    with app.app_context():
        checks = DiagnosticService.run_all_checks()

        assert isinstance(checks, list)
        assert len(checks) > 0

        for check in checks:
            assert "name" in check
            assert "status" in check
            assert "message" in check
            assert check["status"] in ["OK", "AVISO", "ERRO"]