"""Modelos SQLAlchemy — mapeiam exatamente o schema do `appsenhas.sqlite` legado
(ver `migrate_db.py`), então nenhuma migração de dados é necessária: os nomes de
tabela e coluna abaixo são idênticos aos criados pelo código antigo em `app.py`.
"""
from backend.extensions import db
from backend.timezone import agora_sp

TIPO_SETOR_ATENDIMENTO = "atendimento"
TIPO_SETOR_STREAMING = "streaming"
TIPOS_SETOR = {TIPO_SETOR_ATENDIMENTO, TIPO_SETOR_STREAMING}


def normalizar_tipo_setor(valor) -> str:
    tipo = (valor or TIPO_SETOR_ATENDIMENTO).strip().lower()
    if tipo not in TIPOS_SETOR:
        raise ValueError("Tipo do setor deve ser atendimento ou streaming")
    return tipo


def setor_eh_streaming(setor) -> bool:
    if setor is None:
        return False
    return (getattr(setor, "tipo_setor", None) or TIPO_SETOR_ATENDIMENTO) == TIPO_SETOR_STREAMING


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

setor_propagandas_cliente = db.Table(
    "setor_propagandas_cliente",
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
    tipo_setor = db.Column(db.String(20), nullable=False, default=TIPO_SETOR_ATENDIMENTO)
    modo_identificacao_operador = db.Column(db.String(10), nullable=False, default="foto")
    propagandas_ativas = db.Column(db.Boolean, nullable=False, default=False)
    propagandas_cliente_ativas = db.Column(db.Boolean, nullable=False, default=False)
    # Quando True, o tablet do cliente (APK) envia o cupom à impressora na LAN
    # local; o servidor (ex.: atrás de túnel) não tenta abrir TCP na impressora.
    impressao_via_cliente = db.Column(db.Boolean, nullable=False, default=False)
    layout_tv_web = db.Column(db.String(20), nullable=False, default="propaganda")
    orientacao_tv = db.Column(db.String(20), nullable=False, default="horizontal")

    operadores = db.relationship("Operador", backref="setor", lazy="dynamic")
    impressoras = db.relationship("Impressora", backref="setor", lazy="dynamic")
    senhas = db.relationship("Senha", backref="setor", lazy="dynamic")
    propagandas = db.relationship(
        "Propaganda",
        secondary=setor_propagandas,
        back_populates="setores",
        lazy="select",
        overlaps="propagandas_cliente,setores_cliente",
    )
    propagandas_cliente = db.relationship(
        "Propaganda",
        secondary=setor_propagandas_cliente,
        back_populates="setores_cliente",
        lazy="select",
        overlaps="propagandas,setores",
    )

    def to_dict(self):
        return {
            "id": self.id,
            "nome": self.nome,
            "descricao": self.descricao,
            "tipo_setor": self.tipo_setor or TIPO_SETOR_ATENDIMENTO,
            "modo_identificacao_operador": self.modo_identificacao_operador or "foto",
            "propagandas_ativas": bool(self.propagandas_ativas),
            "propagandas_cliente_ativas": bool(self.propagandas_cliente_ativas),
            "impressao_via_cliente": bool(self.impressao_via_cliente),
            "layout_tv_web": self.layout_tv_web or "propaganda",
            "orientacao_tv": self.orientacao_tv or "horizontal",
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
    # Primeiro envio de "adiantar pedido" (não muda se o cliente editar o texto).
    pedido_em = db.Column(db.DateTime)
    data_hora = db.Column(db.DateTime, default=agora_sp)  # retirada (horário de São Paulo)
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
            "pedido_em": self.pedido_em.isoformat() if self.pedido_em else None,
            "data_hora": self.data_hora.isoformat() if self.data_hora else None,
            "chamada_em": self.chamada_em.isoformat() if self.chamada_em else None,
            "finalizado_em": self.finalizado_em.isoformat() if self.finalizado_em else None,
        }


class QrScan(db.Model):
    """Abertura efetiva do acompanhamento via QR (`/acompanhar/<token>`).

    Regra de contagem: **1 registro por senha/token**. Recarregar a página,
    o polling de `/api/verificar_senha/<token>` e reabrir o mesmo link não
    criam outro scan — só o primeiro acesso bem-sucedido é persistido.
    """

    __tablename__ = "qr_scans"

    id = db.Column(db.Integer, primary_key=True)
    senha_id = db.Column(db.Integer, db.ForeignKey("senhas.id"), nullable=False, unique=True)
    setor_id = db.Column(db.Integer, db.ForeignKey("setores.id"))
    scanned_at = db.Column(db.DateTime, default=agora_sp, nullable=False)


class AtendimentoAtual(db.Model):
    __tablename__ = "atendimento_atual"

    id = db.Column(db.Integer, primary_key=True)
    senha_id = db.Column(db.Integer, db.ForeignKey("senhas.id"), nullable=False)
    setor_id = db.Column(db.Integer, db.ForeignKey("setores.id"), nullable=False)
    operador_id = db.Column(db.Integer, db.ForeignKey("operadores.id"), nullable=False)
    data_hora = db.Column(db.DateTime, default=agora_sp)


class Finalizado(db.Model):
    __tablename__ = "finalizados"

    id = db.Column(db.Integer, primary_key=True)
    senha_id = db.Column(db.Integer, db.ForeignKey("senhas.id"), nullable=False)
    operador_id = db.Column(db.Integer, db.ForeignKey("operadores.id"), nullable=False)
    setor_id = db.Column(db.Integer, db.ForeignKey("setores.id"), nullable=False)
    avaliacao = db.Column(db.Text)
    data_hora = db.Column(db.DateTime, default=agora_sp)


class Configuracao(db.Model):
    __tablename__ = "configuracoes"

    id = db.Column(db.Integer, primary_key=True)
    chave = db.Column(db.Text, nullable=False)
    valor = db.Column(db.Text)
    descricao = db.Column(db.Text)
    data_atualizacao = db.Column(db.DateTime, default=agora_sp, onupdate=agora_sp)


class Usuario(db.Model):
    """Usuário do painel administrativo (`/login`, `/admin/*`).

    Papéis:
    - `admin`: acesso total
    - `gerente`: vê apenas os setores vinculados em `usuario_setores`
    - `marketing`: gerencia apenas mídias/propagandas e TVs
    """
    __tablename__ = "usuarios"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.Text, nullable=False, unique=True)
    senha_hash = db.Column(db.Text, nullable=False)
    nome = db.Column(db.Text)
    nome_empresa = db.Column(db.Text)
    papel = db.Column(db.String(20), nullable=False, default="admin")
    criado_em = db.Column(db.DateTime, default=agora_sp)

    setores = db.relationship(
        "Setor",
        secondary="usuario_setores",
        lazy="joined",
    )

    def to_dict(self, *, incluir_setores: bool = True):
        data = {
            "id": self.id,
            "email": self.email,
            "nome": self.nome or "",
            "nome_empresa": self.nome_empresa or "",
            "papel": (self.papel or "admin").strip().lower(),
            "criado_em": self.criado_em.isoformat() if self.criado_em else None,
        }
        if incluir_setores:
            data["setor_ids"] = [s.id for s in (self.setores or [])]
            data["setores"] = [{"id": s.id, "nome": s.nome} for s in (self.setores or [])]
        return data


usuario_setores = db.Table(
    "usuario_setores",
    db.Column("usuario_id", db.Integer, db.ForeignKey("usuarios.id"), primary_key=True),
    db.Column("setor_id", db.Integer, db.ForeignKey("setores.id"), primary_key=True),
)


class Propaganda(db.Model):
    """Mídia publicitária (imagem ou vídeo) vinculável a um ou mais setores/TVs."""

    __tablename__ = "propagandas"

    id = db.Column(db.Integer, primary_key=True)
    arquivo = db.Column(db.Text, nullable=False)
    tipo = db.Column(db.String(10), nullable=False, default="image")  # image | video
    ordem = db.Column(db.Integer, nullable=False, default=0)
    ativo = db.Column(db.Boolean, nullable=False, default=True)
    criado_em = db.Column(db.DateTime, default=agora_sp)
    setores = db.relationship(
        "Setor",
        secondary=setor_propagandas,
        back_populates="propagandas",
        lazy="select",
        overlaps="propagandas_cliente,setores_cliente",
    )
    setores_cliente = db.relationship(
        "Setor",
        secondary=setor_propagandas_cliente,
        back_populates="propagandas_cliente",
        lazy="select",
        overlaps="propagandas,setores",
    )

    def to_dict(self):
        return {
            "id": self.id,
            "arquivo": self.arquivo,
            "tipo": (self.tipo or "image"),
            "ordem": self.ordem,
            "ativo": bool(self.ativo),
            "criado_em": self.criado_em.isoformat() if self.criado_em else None,
            "setor_ids": sorted(setor.id for setor in self.setores),
            "setor_ids_cliente": sorted(setor.id for setor in self.setores_cliente),
        }


dispositivo_propagandas = db.Table(
    "dispositivo_propagandas",
    db.Column(
        "dispositivo_id",
        db.Integer,
        db.ForeignKey("tv_dispositivos.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    db.Column(
        "propaganda_id",
        db.Integer,
        db.ForeignKey("propagandas.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    db.Column("ordem", db.Integer, nullable=False, default=0),
)


class TvDispositivo(db.Model):
    """TV registrada: cliente de streaming legado ou painel de senha de um setor."""

    __tablename__ = "tv_dispositivos"

    id = db.Column(db.Integer, primary_key=True)
    tipo = db.Column(db.String(20), nullable=False, default="streaming")  # streaming | setor
    chave = db.Column(db.Text, nullable=False, unique=True)
    nome = db.Column(db.Text, nullable=False)
    device_name = db.Column(db.Text)
    user_agent = db.Column(db.Text)
    last_seen = db.Column(db.DateTime, default=agora_sp)
    is_online = db.Column(db.Boolean, nullable=False, default=False)
    # Orientação física desta TV de streaming (independente do setor).
    orientacao_tv = db.Column(db.String(20), nullable=False, default="horizontal")
    setor_id = db.Column(db.Integer, db.ForeignKey("setores.id", ondelete="SET NULL"))
    criado_em = db.Column(db.DateTime, default=agora_sp)

    setor = db.relationship("Setor", lazy="joined")
    propagandas = db.relationship(
        "Propaganda",
        secondary=dispositivo_propagandas,
        lazy="select",
    )

    def to_admin_dict(self, *, online: bool | None = None, propaganda_ids: list[int] | None = None):
        return {
            "id": self.id,
            "tipo": self.tipo,
            "chave": self.chave,
            "nome": self.nome,
            "device_name": self.device_name or "",
            "user_agent": self.user_agent or "",
            "last_seen": self.last_seen.isoformat() if self.last_seen else None,
            "is_online": bool(self.is_online if online is None else online),
            "orientacao_tv": self.orientacao_tv or "horizontal",
            "setor_id": self.setor_id,
            "setor_nome": self.setor.nome if self.setor else None,
            "tipo_setor": (self.setor.tipo_setor or TIPO_SETOR_ATENDIMENTO) if self.setor else None,
            "propaganda_ids": propaganda_ids if propaganda_ids is not None else [],
        }
