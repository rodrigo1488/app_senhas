"""Modelos SQLAlchemy — mapeiam exatamente o schema do `appsenhas.sqlite` legado
(ver `migrate_db.py`), então nenhuma migração de dados é necessária: os nomes de
tabela e coluna abaixo são idênticos aos criados pelo código antigo em `app.py`.
"""
from datetime import datetime

from backend.extensions import db


class Setor(db.Model):
    __tablename__ = "setores"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.Text, nullable=False)
    descricao = db.Column(db.Text)
    senha_setor = db.Column(db.Text)  # "código do setor" usado no login do app/kiosk
    modo_identificacao_operador = db.Column(db.String(10), nullable=False, default="foto")

    operadores = db.relationship("Operador", backref="setor", lazy="dynamic")
    impressoras = db.relationship("Impressora", backref="setor", lazy="dynamic")
    senhas = db.relationship("Senha", backref="setor", lazy="dynamic")

    def to_dict(self):
        return {
            "id": self.id,
            "nome": self.nome,
            "descricao": self.descricao,
            "modo_identificacao_operador": self.modo_identificacao_operador or "foto",
        }


class Operador(db.Model):
    __tablename__ = "operadores"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.Text, nullable=False)
    foto_perfil = db.Column(db.Text)
    setor_id = db.Column(db.Integer, db.ForeignKey("setores.id"))
    pin_hash = db.Column(db.Text)

    def to_dict(self):
        return {
            "id": self.id,
            "nome": self.nome,
            "foto_perfil": self.foto_perfil,
            "setor_id": self.setor_id,
            "tem_pin": bool(self.pin_hash),
        }


class Impressora(db.Model):
    __tablename__ = "impressoras"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.Text, nullable=False)
    ip = db.Column(db.Text, nullable=False)
    porta = db.Column(db.Integer, default=9100)
    setor_id = db.Column(db.Integer, db.ForeignKey("setores.id"))


class Senha(db.Model):
    __tablename__ = "senhas"

    id = db.Column(db.Integer, primary_key=True)
    senha = db.Column(db.Text, nullable=False)
    tipo = db.Column(db.Text, nullable=False)  # 'normal' | 'preferencial'
    setor_id = db.Column(db.Integer, db.ForeignKey("setores.id"))
    status = db.Column(db.Text, default="A")  # A=Aguardando, C=Chamada, F=Finalizada
    token_unico = db.Column(db.Text, unique=True)
    notificado = db.Column(db.Integer, default=0)
    push_subscription = db.Column(db.Text)
    pedido = db.Column(db.Text)
    tem_pedido = db.Column(db.Boolean, default=False)
    pedido_confirmado = db.Column(db.Boolean, default=False)
    data_hora = db.Column(db.DateTime, default=datetime.now)

    def to_dict(self):
        return {
            "id": self.id,
            "senha": self.senha,
            "tipo": self.tipo,
            "setor_id": self.setor_id,
            "status": self.status,
            "token_unico": self.token_unico,
            "tem_pedido": bool(self.tem_pedido),
            "pedido": self.pedido,
            "pedido_confirmado": bool(self.pedido_confirmado),
        }


class AtendimentoAtual(db.Model):
    __tablename__ = "atendimento_atual"

    id = db.Column(db.Integer, primary_key=True)
    senha_id = db.Column(db.Integer, db.ForeignKey("senhas.id"), nullable=False)
    setor_id = db.Column(db.Integer, db.ForeignKey("setores.id"), nullable=False)
    operador_id = db.Column(db.Integer, db.ForeignKey("operadores.id"), nullable=False)
    data_hora = db.Column(db.DateTime, default=datetime.now)


class Finalizado(db.Model):
    __tablename__ = "finalizados"

    id = db.Column(db.Integer, primary_key=True)
    senha_id = db.Column(db.Integer, db.ForeignKey("senhas.id"), nullable=False)
    operador_id = db.Column(db.Integer, db.ForeignKey("operadores.id"), nullable=False)
    setor_id = db.Column(db.Integer, db.ForeignKey("setores.id"), nullable=False)
    avaliacao = db.Column(db.Text)
    data_hora = db.Column(db.DateTime, default=datetime.now)


class Configuracao(db.Model):
    __tablename__ = "configuracoes"

    id = db.Column(db.Integer, primary_key=True)
    chave = db.Column(db.Text, nullable=False)
    valor = db.Column(db.Text)
    descricao = db.Column(db.Text)
    data_atualizacao = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)


class Usuario(db.Model):
    """Usuário administrador do painel (`/login`, `/admin/*`).

    Substitui o login via Supabase (tabela `users` externa) por uma tabela
    local — elimina a dependência de um serviço externo só para autenticar
    o admin. Ver `backend/services/usuario_service.py` e
    `backend/blueprints/auth_bp.py`.
    """
    __tablename__ = "usuarios"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.Text, nullable=False, unique=True)
    senha_hash = db.Column(db.Text, nullable=False)
    nome_empresa = db.Column(db.Text)
    criado_em = db.Column(db.DateTime, default=datetime.now)
