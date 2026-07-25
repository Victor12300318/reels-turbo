export default function PrivacyPolicyPage() {
  return (
    <div className="min-h-screen bg-[#090d16] text-slate-200 p-6 md:p-12">
      <div className="max-w-3xl mx-auto space-y-6">
        <h1 className="text-2xl font-bold text-white">Política de Privacidade</h1>
        <p className="text-xs text-slate-400">Última atualização: 25 de Julho de 2026</p>

        <section className="space-y-2">
          <h2 className="text-lg font-semibold text-indigo-400">1. Introdução</h2>
          <p className="text-sm text-slate-300 leading-relaxed">
            O Reels Cloner AI ("nós", "nosso" ou "aplicativo") respeita a privacidade dos seus usuários. Esta Política de Privacidade descreve como coletamos, usamos, armazenamos e protegemos seus dados pessoais ao utilizar nossa plataforma de clonagem e automação de Reels do Instagram.
          </p>
        </section>

        <section className="space-y-2">
          <h2 className="text-lg font-semibold text-indigo-400">2. Dados Coletados</h2>
          <p className="text-sm text-slate-300 leading-relaxed">
            Coletamos as seguintes informações:
          </p>
          <ul className="text-sm text-slate-300 list-disc list-inside space-y-1">
            <li><strong>E-mail e senha:</strong> Para autenticação na plataforma.</li>
            <li><strong>Vídeos enviados:</strong> Vídeos locais enviados pelo usuário para a biblioteca de clonagem.</li>
            <li><strong>Links de Reels do Instagram:</strong> URLs enviadas para processamento de clonagem.</li>
            <li><strong>Credenciais do Instagram (Meta Graph API):</strong> ID da conta e token de acesso para postagem automática.</li>
            <li><strong>Cookies do Instagram:</strong> Utilizados exclusivamente para download de Reels via yt-dlp.</li>
          </ul>
        </section>

        <section className="space-y-2">
          <h2 className="text-lg font-semibold text-indigo-400">3. Como Usamos Seus Dados</h2>
          <p className="text-sm text-slate-300 leading-relaxed">
            Seus dados são utilizados para: processar e clonar Reels do Instagram, armazenar vídeos na nuvem (MinIO/S3), publicar automaticamente Reels no seu perfil do Instagram através da Meta Graph API, e fornecer métricas e relatórios no painel.
          </p>
        </section>

        <section className="space-y-2">
          <h2 className="text-lg font-semibold text-indigo-400">4. Armazenamento e Segurança</h2>
          <p className="text-sm text-slate-300 leading-relaxed">
            Seus dados são armazenados em banco de dados PostgreSQL com senhas criptografadas usando PBKDF2-HMAC-SHA256 com salt individual. Vídeos são armazenados em buckets privados do MinIO/S3. Utilizamos JWT (JSON Web Tokens) com expiração para autenticação de sessão.
          </p>
        </section>

        <section className="space-y-2">
          <h2 className="text-lg font-semibold text-indigo-400">5. Permissões do Instagram (Meta Graph API)</h2>
          <p className="text-sm text-slate-300 leading-relaxed">
            O aplicativo solicita as seguintes permissões da Meta: <code className="text-indigo-300">instagram_basic</code>, <code className="text-indigo-300">instagram_content_publish</code>, <code className="text-indigo-300">pages_show_list</code> e <code className="text-indigo-300">pages_read_engagement</code>. Estas permissões são usadas exclusivamente para publicar Reels no seu perfil.
          </p>
        </section>

        <section className="space-y-2">
          <h2 className="text-lg font-semibold text-indigo-400">6. Compartilhamento de Dados</h2>
          <p className="text-sm text-slate-300 leading-relaxed">
            Não vendemos, alugamos ou compartilhamos seus dados com terceiros. Os dados são processados exclusivamente dentro da nossa infraestrutura e da Meta Graph API (para postagem no Instagram).
          </p>
        </section>

        <section className="space-y-2">
          <h2 className="text-lg font-semibold text-indigo-400">7. Seus Direitos (LGPD)</h2>
          <p className="text-sm text-slate-300 leading-relaxed">
            Você tem o direito de acessar, corrigir ou excluir seus dados pessoais a qualquer momento. Para solicitar a exclusão completa dos seus dados, visite nossa <a href="/data-deletion" className="text-indigo-400 underline">página de exclusão de dados</a>.
          </p>
        </section>

        <section className="space-y-2">
          <h2 className="text-lg font-semibold text-indigo-400">8. Contato</h2>
          <p className="text-sm text-slate-300 leading-relaxed">
            Para dúvidas sobre privacidade, entre em contato através do e-mail do administrador do sistema.
          </p>
        </section>
      </div>
    </div>
  )
}
