# Publicar o CompuFlow Senhas na Play Store

## 1. Arquivos desta pasta

| Arquivo | Uso no Play Console |
| --- | --- |
| `CompuFlow-senhas-1.13.aab` | Produção → Criar versão → Enviar app bundle |
| `graficos/icon-512.png` | Ícone de alta resolução (512 × 512) |
| `graficos/feature-1024x500.png` | Gráfico de recurso (1024 × 500) |
| `graficos/phone-1.png` e `phone-2.png` | Capturas de telefone (mínimo 2) |
| `listing/pt-BR/` | Ficha da loja em português |
| `politica-privacidade.html` | Publique em um site HTTPS e informe a URL |
| `declaracao-dados.txt` | Apoio ao formulário de Segurança dos dados |

## 2. Passos no console

1. Acesse [Google Play Console](https://play.google.com/console) com a conta da empresa.
2. Crie um app: nome **CompuFlow Senhas**, idioma padrão **português (Brasil)**, gratuito.
3. Preencha a ficha da loja com os textos de `listing/pt-BR/` e os gráficos.
4. Informe a URL da política de privacidade.
5. Complete classificação de conteúdo e Segurança dos dados (`declaracao-dados.txt`).
6. Em Produção (ou teste interno), envie o `.aab`.
7. Envie para revisão.

## 3. Gerar de novo o pacote

No computador, com o JDK 21 já configurado:

```bat
cd app
gradlew.bat :app:bundleRelease
```

O `.aab` sai em `app/app/build/outputs/bundle/release/app-release.aab`. Copie para esta pasta se for republicar.

## 4. Assinatura (não perder)

O arquivo `app/play-release.jks` e as senhas em `playstore/credenciais-assinatura.txt` **não vão para o Git**. Faça backup. Sem eles, a Play Store não aceita atualizações deste app.
