# Hook personalizado para PyInstaller - Eventlet
# Este arquivo deve ser colocado em: PyInstaller/hooks/hook-eventlet.py
# Ou adicionado ao hookspath no .spec

from PyInstaller.utils.hooks import collect_submodules, collect_data_files

# Coletar todos os submódulos do eventlet
hiddenimports = collect_submodules('eventlet')

# Adicionar módulos específicos que podem ser carregados dinamicamente
hiddenimports += [
    'eventlet.hubs.epolls',
    'eventlet.hubs.kqueue',
    'eventlet.hubs.selects',
    'eventlet.hubs.poll',
    'eventlet.hubs.pyevent',
    'eventlet.hubs.timer',
    'eventlet.green._socket_nodns',
    'eventlet.support.greendns',
]

# Coletar arquivos de dados do eventlet se houver
datas = collect_data_files('eventlet', includes=['*.py', '*.txt', '*.md'])

