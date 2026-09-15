"""Modelos SQLAlchemy — mapeiam exatamente o schema do `appsenhas.sqlite` legado
(ver `migrate_db.py`), então nenhuma migração de dados é necessária: os nomes de
tabela e coluna abaixo são idênticos aos criados pelo código antigo em `app.py`.
"""
from datetime import datetime

from backend.extensions import db


setor_propagandas = db.Table(
    "setor_propagandas",
    db.Column("setor_id", db.Integer, db.ForeignKey("setores.id", ondelete="CASCADE"), primary_key=True),
    db.Column(
        "propaganda_id",
        db.Integer,
        db.ForeignKey("propagandas.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)


class Setor(db.Model):
    __tablename__ = "setores"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.Text, nullable=False)
    descricao = db.Column(db.Text)
    senha_setor = db.Column(db.Text)  # "código do setor" usado no login do app/kiosk
    modo_identificacao_operador = db.Column(db.String(10), nullable=False, default="foto")
    propagandas_ativas = db.Column(db.Boolean, nullable=False, default=False)
    layout_tv_web = db.Column(db.String(20), nullable=False, default="propaganda")

    operadores = db.relationship("Operador", backref="setor", lazy="dynamic")
    impressoras = db.relationship("Impressora", backref="setor", lazy="dynamic")
    senhas = db.relationship("Senha", backref="setor", lazy="dynamic")
    propagandas = db.relationship(
        "Propaganda",
        secondary=setor_propagandas,
        back_populates="setores",
        lazy="select",
    )

    def to_dict(self):
        return {
            "id": self.id,
            "nome": self.nome,
            "descricao": self.descricao,
            "modo_identificacao_operador": self.modo_identificacao_operador or "foto",
            "propagandas_ativas": bool(self.propagandas_ativas),
            "layout_tv_web": self.layout_tv_web or "propaganda",
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
    data_hora = db.Column(db.DateTime, default=datetime.now)  # retirada
    # Persistidos no ciclo de vida para analytics (espera = chamada_em - data_hora;
    # atendimento = finalizado_em - chamada_em). AtendimentoAtual é apagado ao
    # finalizar, então sem estes campos não há histórico de espera.
    chamada_em = db.Column(db.DateTime)
    finalizado_em = db.Column(db.DateTime)

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
            "data_hora": self.data_hora.isoformat() if self.data_hora else None,
            "chamada_em": self.chamada_em.isoformat() if self.chamada_em else None,
            "finalizado_em": self.finalizado_em.isoformat() if self.finalizado_em else None,
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


class Propaganda(db.Model):
    """Imagem publicitária vinculável a um ou mais setores."""

    __tablename__ = "propagandas"

    id = db.Column(db.Integer, primary_key=True)
    arquivo = db.Column(db.Text, nullable=False)
    ordem = db.Column(db.Integer, nullable=False, default=0)
    ativo = db.Column(db.Boolean, nullable=False, default=True)
    criado_em = db.Column(db.DateTime, default=datetime.now)
    setores = db.relationship(
        "Setor",
        secondary=setor_propagandas,
        back_populates="propagandas",
        lazy="select",
    )

    def to_dict(self):
        return {
            "id": self.id,
            "arquivo": self.arquivo,
            "ordem": self.ordem,
            "ativo": bool(self.ativo),
            "criado_em": self.criado_em.isoformat() if self.criado_em else None,
            "setor_ids": sorted(setor.id for setor in self.setores),
        }
