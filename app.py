"""Ponto de entrada da aplicação.

Mantido como `app.py` na raiz (mesmo nome do arquivo legado) por
compatibilidade com o pipeline de build existente (`build_executable.bat`,
`test_imports.py`, `diagnostico_build.py`) e com o PyInstaller, que gera o
`.spec` apontando para este arquivo.

Toda a lógica da aplicação vive agora no pacote `backend/` (app factory,
blueprints, services, sockets — ver `backend/__init__.py` e
`documentacao/REALTIME_PROTOCOL.md`). O monólito antigo foi preservado em
`app_legacy.py.bak` apenas como referência histórica.

IMPORTANTE: `eventlet.monkey_patch()` precisa rodar antes de qualquer outro
import de rede/threading — por isso é a primeira linha executável deste
módulo, exatamente como no código legado.
"""
import eventlet

eventlet.monkey_patch()

from backend import create_app  # noqa: E402
from backend.extensions import socketio  # noqa: E402

app = create_app()

if __name__ == "__main__":
    print("[HTTP] Iniciando aplicativo...")
    print("[HTTP] Protocolo de tempo real: ver documentacao/REALTIME_PROTOCOL.md")
    print("[HTTP] Acesse: http://<seu-ip-local>:5000")
    socketio.run(app, host="0.0.0.0", port=5000, debug=True)
