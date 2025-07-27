// Sistema de 5 cliques consecutivos para redirecionamento
// Funcionalidade implementada em todas as páginas principais

// Variáveis para controle de cliques consecutivos
let clickCount = 0;
let clickTimer = null;
const CLICK_TIMEOUT = 2000; // 2 segundos para considerar cliques consecutivos
const REQUIRED_CLICKS = 5; // Número de cliques necessários

// Função para detectar cliques consecutivos
function handleConsecutiveClicks() {
    clickCount++;
    console.log(`Clique ${clickCount}/${REQUIRED_CLICKS} registrado`);
    
    // Limpa o timer anterior se existir
    if (clickTimer) {
        clearTimeout(clickTimer);
    }
    
    // Se atingiu o número de cliques necessários
    if (clickCount >= REQUIRED_CLICKS) {
        console.log('5 cliques consecutivos detectados! Redirecionando para /setores...');
        try {
            window.location.href = '/setores';
        } catch (error) {
            console.error('Erro ao redirecionar:', error);
            // Fallback: tenta redirecionar de outra forma
            window.location.replace('/setores');
        }
        return;
    }
    
    // Define um timer para resetar o contador se não houver mais cliques
    clickTimer = setTimeout(function() {
        console.log('Timer expirado. Contador de cliques resetado.');
        clickCount = 0;
    }, CLICK_TIMEOUT);
}

// Função para inicializar o sistema de cliques
function initConsecutiveClicks() {
    console.log('Inicializando sistema de 5 cliques...');
    
    // Adiciona o evento de clique ao documento (qualquer lugar da tela)
    document.addEventListener('click', function(event) {
        console.log('Clique detectado em:', event.target.tagName, event.target.className);
        
        // Evita que cliques nos elementos interativos sejam contados
        if (event.target.tagName === 'A' || 
            event.target.tagName === 'BUTTON' || 
            event.target.tagName === 'INPUT' ||
            event.target.tagName === 'SELECT' ||
            event.target.tagName === 'TEXTAREA' ||
            event.target.closest('form') !== null ||
            event.target.closest('a') !== null ||
            event.target.closest('button') !== null) {
            console.log('Clique ignorado - elemento interativo');
            return;
        }
        
        console.log('Clique válido contado. Total:', clickCount + 1);
        handleConsecutiveClicks();
    });

    // Log inicial para debug
    console.log('Sistema de 5 cliques ativado. Clique 5 vezes em qualquer lugar da tela para ir para /setores');
}

// Inicializa o sistema quando o DOM estiver carregado
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initConsecutiveClicks);
} else {
    initConsecutiveClicks();
} 