// Service Worker para notificações push
const CACHE_NAME = 'senhas-notification-v1';

// Instalar service worker
self.addEventListener('install', function(event) {
    console.log('[SW] Service Worker instalado');
    self.skipWaiting();
});

// Ativar service worker
self.addEventListener('activate', function(event) {
    console.log('[SW] Service Worker ativado');
    event.waitUntil(self.clients.claim());
});

// Interceptar push notifications
self.addEventListener('push', function(event) {
    console.log('[SW] Push notification recebida:', event);
    
    let notificationData = {
        title: 'Sua senha foi chamada!',
        body: 'Dirija-se ao atendimento.',
        icon: '/static/icon-192x192.png',
        badge: '/static/badge-72x72.png',
        tag: 'senha-chamada',
        requireInteraction: true,
        actions: [
            {
                action: 'ver',
                title: 'Ver Detalhes',
                icon: '/static/icon-192x192.png'
            },
            {
                action: 'fechar',
                title: 'Fechar',
                icon: '/static/icon-192x192.png'
            }
        ]
    };
    
    // Se há dados no push, usar eles
    if (event.data) {
        try {
            const data = event.data.json();
            notificationData = {
                ...notificationData,
                ...data
            };
        } catch (e) {
            console.log('[SW] Erro ao parsear dados do push:', e);
        }
    }
    
    event.waitUntil(
        self.registration.showNotification(notificationData.title, notificationData)
    );
});

// Interceptar cliques na notificação
self.addEventListener('notificationclick', function(event) {
    console.log('[SW] Notificação clicada:', event);
    
    event.notification.close();
    
    if (event.action === 'ver') {
        // Abrir a página principal
        event.waitUntil(
            self.clients.openWindow('/')
        );
    } else if (event.action === 'fechar') {
        // Apenas fechar a notificação
        return;
    } else {
        // Clique na notificação principal - abrir página
        event.waitUntil(
            self.clients.openWindow('/')
        );
    }
});

// Interceptar fechamento da notificação
self.addEventListener('notificationclose', function(event) {
    console.log('[SW] Notificação fechada:', event);
});

// Interceptar mensagens do cliente
self.addEventListener('message', function(event) {
    console.log('[SW] Mensagem recebida:', event.data);
    
    if (event.data && event.data.type === 'SKIP_WAITING') {
        self.skipWaiting();
    }
}); 