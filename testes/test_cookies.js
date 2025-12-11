// Script para testar o sistema de cookies
// Execute no console do navegador na página de notificação

console.log('🧪 Testando sistema de cookies...');

// Funções de Cookie
function setCookie(name, value, hours = 2) {
    const expires = new Date();
    expires.setTime(expires.getTime() + (hours * 60 * 60 * 1000));
    document.cookie = `${name}=${value};expires=${expires.toUTCString()};path=/;SameSite=Lax`;
    console.log(`Cookie ${name} definido:`, value);
}

function getCookie(name) {
    const nameEQ = name + "=";
    const ca = document.cookie.split(';');
    for(let i = 0; i < ca.length; i++) {
        let c = ca[i];
        while (c.charAt(0) === ' ') c = c.substring(1, c.length);
        if (c.indexOf(nameEQ) === 0) return c.substring(nameEQ.length, c.length);
    }
    return null;
}

function deleteCookie(name) {
    document.cookie = `${name}=;expires=Thu, 01 Jan 1970 00:00:00 UTC;path=/;`;
    console.log(`Cookie ${name} removido`);
}

// Teste 1: Definir cookie
console.log('\n📝 Teste 1: Definir cookie');
const testConfig = {
    token: 'teste-123',
    soundEnabled: true,
    isMonitoring: true,
    timestamp: new Date().toISOString()
};
setCookie('senha_config', JSON.stringify(testConfig), 2);

// Teste 2: Ler cookie
console.log('\n📖 Teste 2: Ler cookie');
const configStr = getCookie('senha_config');
console.log('Cookie lido:', configStr);

if (configStr) {
    try {
        const config = JSON.parse(configStr);
        console.log('Configuração parseada:', config);
        console.log('Token:', config.token);
        console.log('Som ativado:', config.soundEnabled);
        console.log('Monitoramento ativo:', config.isMonitoring);
        console.log('Timestamp:', new Date(config.timestamp).toLocaleString());
    } catch (e) {
        console.error('Erro ao fazer parse:', e);
    }
}

// Teste 3: Verificar todos os cookies
console.log('\n🍪 Teste 3: Todos os cookies');
console.log('document.cookie:', document.cookie);

// Teste 4: Simular configuração de monitoramento
console.log('\n⚙️ Teste 4: Simular configuração de monitoramento');
const monitorConfig = {
    token: 'teste-456',
    soundEnabled: false,
    isMonitoring: true,
    timestamp: new Date().toISOString()
};
setCookie('senha_config', JSON.stringify(monitorConfig), 2);

// Teste 5: Verificar se carregou corretamente
console.log('\n✅ Teste 5: Verificar carregamento');
const loadedConfig = getCookie('senha_config');
if (loadedConfig) {
    const config = JSON.parse(loadedConfig);
    console.log('Configuração carregada:', config);
    console.log('Som ativado:', config.soundEnabled ? '✅' : '❌');
    console.log('Monitoramento ativo:', config.isMonitoring ? '✅' : '❌');
}

console.log('\n🎉 Testes de cookie concluídos!');
console.log('Para limpar cookies: deleteCookie("senha_config")'); 