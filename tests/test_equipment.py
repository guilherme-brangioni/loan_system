from models.equipment import Equipment


def test_admin_can_create_equipment(client, app, login_user):
    """
    ADMIN consegue cadastrar item.
    """

    login_user(role="ADMIN")

    response = client.post(
        "/itens/novo",
        data={
            "fabricante": "FLUKE",
            "modelo": "87V",
            "tipo_equipamento": "MULTIMETRO",
            "patrimonio": "N/A",
            "codigo_equipamento": "EQ-TEST-001",
            "serial": "SN-TEST-001",
            "categoria": "MEDICAO",
            "observacoes": "Item criado em teste automatizado.",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200

    with app.app_context():
        equipment = Equipment.query.filter_by(
            codigo_equipamento="EQ-TEST-001"
        ).first()

        assert equipment is not None
        assert equipment.fabricante == "FLUKE"
        assert equipment.modelo == "87V"
        assert equipment.tipo_equipamento == "MULTIMETRO"
        assert equipment.patrimonio == "N/A"
        assert equipment.serial == "SN-TEST-001"
        assert equipment.validado is True


def test_operator_can_create_equipment(client, app, login_user):
    """
    OPERADOR também consegue cadastrar item.
    """

    login_user(
        email="operador@teste.com",
        role="OPERADOR",
    )

    response = client.post(
        "/itens/novo",
        data={
            "fabricante": "DELL",
            "modelo": "LATITUDE 5420",
            "tipo_equipamento": "NOTEBOOK",
            "patrimonio": "N/A",
            "codigo_equipamento": "EQ-TEST-002",
            "serial": "SN-TEST-002",
            "categoria": "INFORMATICA",
            "observacoes": "",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200

    with app.app_context():
        equipment = Equipment.query.filter_by(
            codigo_equipamento="EQ-TEST-002"
        ).first()

        assert equipment is not None
        assert equipment.fabricante == "DELL"


def test_consulta_cannot_create_equipment(client, app, login_user):
    """
    CONSULTA pode visualizar, mas não pode executar POST.
    """

    login_user(
        email="consulta@teste.com",
        role="CONSULTA",
    )

    response = client.post(
        "/itens/novo",
        data={
            "fabricante": "HP",
            "modelo": "TESTE",
            "tipo_equipamento": "NOTEBOOK",
            "patrimonio": "N/A",
            "codigo_equipamento": "EQ-BLOCKED",
            "serial": "SN-BLOCKED",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert "Seu perfil é somente consulta".encode("utf-8") in response.data

    with app.app_context():
        equipment = Equipment.query.filter_by(
            codigo_equipamento="EQ-BLOCKED"
        ).first()

        assert equipment is None


def test_equipment_requires_identification_when_patrimonio_na(
    client,
    app,
    login_user,
):
    """
    Se patrimônio for N/A, precisa ter série ou código do equipamento.
    """

    login_user(role="ADMIN")

    response = client.post(
        "/itens/novo",
        data={
            "fabricante": "TESTE",
            "modelo": "MODELO",
            "tipo_equipamento": "TIPO",
            "patrimonio": "N/A",
            "codigo_equipamento": "",
            "serial": "",
            "categoria": "",
            "observacoes": "",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert "Quando o patrimônio for N/A".encode("utf-8") in response.data

    with app.app_context():
        equipment = Equipment.query.filter_by(
            fabricante="TESTE"
        ).first()

        assert equipment is None