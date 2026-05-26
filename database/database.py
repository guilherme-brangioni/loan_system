from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate


# db será usado por todos os models.
db = SQLAlchemy()

# migrate permite criar e aplicar migrations no banco.
migrate = Migrate()