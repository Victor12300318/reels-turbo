# Meta App & Instagram OAuth Setup Guide

Este documento detalha o passo a passo para configurar a aplicação Meta Developer e autenticar contas do Instagram Graph API no **Reels Cloner AI**.

---

## 1. Criar Aplicativo na Meta for Developers
1. Acesse [developers.facebook.com](https:/developers.facebook.com/).
2. Clique em **Meus Aplicativos** > **Criar Aplicativo**.
3. Selecione o tipo de aplicativo: **Empresa** (Business) ou **Outro**.
4. Defina o nome do aplicativo (ex: *Reels Cloner AI*) e vincule sua Conta Comercial do Meta (Meta Business Suite).

---

## 2. Configurar o Produto "Instagram Graph API" ou "Facebook Login"
1. No painel do seu aplicativo, clique em **Adicionar Produto**.
2. Adicione **Instagram Graph API** e **Login do Facebook**.
3. Nas configurações do **Login do Facebook**, adicione a URL de redirecionamento OAuth válida:
   - `https:/reelsturbo.hdstec.com.br/api/v1/auth/instagram/callback`
   - *(Em desenvolvimento local: `http:/localhost:8000/api/v1/auth/instagram/callback`)*

---

## 3. Configurações de Privacidade e Termos
A Meta exige que o aplicativo possua URLs públicas de Política de Privacidade e Termos de Uso configuradas no painel básico do aplicativo:
- **Política de Privacidade:** `https:/reelsturbo.hdstec.com.br/privacy`
- **Termos de Serviço:** `https:/reelsturbo.hdstec.com.br/terms`
- **Exclusão de Dados (Data Deletion Callback):** `https:/reelsturbo.hdstec.com.br/api/v1/auth/instagram/data-deletion`

---

## 4. Variáveis de Ambiente (`.env`)
Insira as credenciais geradas no arquivo `.env` do projeto:

```env
META_APP_ID=1337818285188918
META_APP_SECRET=sua_chave_secreta_meta
INSTAGRAM_CLIENT_ID=913982567729553
INSTAGRAM_CLIENT_SECRET=sua_chave_secreta_instagram
INSTAGRAM_REDIRECT_URI=https://reelsturbo.hdstec.com.br/api/v1/auth/instagram/callback
INSTAGRAM_ACCOUNT_ID=seu_instagram_business_account_id
INSTAGRAM_ACCESS_TOKEN=seu_token_de_acesso_longo
```

---

## 5. Permissões Necessárias (Scopes)
Para publicar Reels automaticamente, o token gerado pelo OAuth deve conter os seguintes escopos:
- `instagram_basic`
- `instagram_content_publish`
- `pages_show_list`
- `pages_read_engagement`
