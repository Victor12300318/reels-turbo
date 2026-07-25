export default function DataDeletionPage() {
  return (
    <div className="min-h-screen bg-[#090d16] text-slate-200 p-6 md:p-12">
      <div className="max-w-3xl mx-auto space-y-6">
        <h1 className="text-2xl font-bold text-white">Exclusão de Dados</h1>
        <p className="text-xs text-slate-400">Última atualização: 25 de Julho de 2026</p>

        <section className="space-y-2">
          <h2 className="text-lg font-semibold text-indigo-400">Como Solicitar a Exclusão dos Seus Dados</h2>
          <p className="text-sm text-slate-300 leading-relaxed">
            Você tem o direito de solicitar a exclusão completa de todos os seus dados pessoais da plataforma Reels Cloner AI a qualquer momento, em conformidade com a LGPD (Lei Geral de Proteção de Dados) e as políticas da Meta.
          </p>
        </section>

        <section className="space-y-2">
          <h2 className="text-lg font-semibold text-indigo-400">O Que Será Excluído</h2>
          <ul className="text-sm text-slate-300 list-disc list-inside space-y-1">
            <li>Sua conta de usuário (e-mail, senha criptografada e API Key).</li>
            <li>Todos os vídeos enviados para a biblioteca local.</li>
            <li>Todos os Reels clonados e processados.</li>
            <li>Credenciais do Instagram (Account ID e Access Token).</li>
            <li>Histórico de jobs, agendamentos e postagens.</li>
            <li>Configurações personalizadas (legendas fixas, preferências de postagem).</li>
          </ul>
        </section>

        <section className="space-y-2">
          <h2 className="text-lg font-semibold text-indigo-400">Como Solicitar</h2>
          <p className="text-sm text-slate-300 leading-relaxed">
            Para solicitar a exclusão dos seus dados, envie um e-mail para o administrador do sistema com o assunto <strong>"Solicitação de Exclusão de Dados"</strong> informando o e-mail cadastrado na plataforma.
          </p>
          <p className="text-sm text-slate-300 leading-relaxed">
            A exclusão será processada em até <strong>72 horas</strong>. Após a exclusão, todos os seus dados serão permanentemente removidos do banco de dados e do armazenamento em nuvem (S3/MinIO), sem possibilidade de recuperação.
          </p>
        </section>

        <section className="space-y-2">
          <h2 className="text-lg font-semibold text-indigo-400">Callback da Meta</h2>
          <p className="text-sm text-slate-300 leading-relaxed">
            Se você conectou sua conta do Instagram através do login OAuth da Meta, a solicitação de exclusão de dados também pode ser iniciada através das configurações do seu Facebook/Instagram. Neste caso, a Meta enviará um callback para o nosso endpoint de exclusão de dados e processaremos a remoção automaticamente.
          </p>
        </section>

        <div className="rounded-xl border border-amber-500/20 bg-amber-950/30 p-4">
          <p className="text-xs text-amber-300">
            ⚠️ <strong>Atenção:</strong> A exclusão de dados é irreversível. Todos os seus Reels clonados, agendamentos e vídeos da biblioteca serão permanentemente perdidos.
          </p>
        </div>
      </div>
    </div>
  )
}
