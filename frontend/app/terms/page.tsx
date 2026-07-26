export default function TermsOfServicePage() {
  return (
    <div className="min-h-screen bg-[#090d16] text-slate-200 p-6 md:p-12">
      <div className="max-w-3xl mx-auto space-y-6">
        <h1 className="text-2xl font-bold text-white">Termos de Uso</h1>
        <p className="text-xs text-slate-400">Última atualização: 25 de Julho de 2026</p>

        <section className="space-y-2">
          <h2 className="text-lg font-semibold text-indigo-400">1. Aceitação dos Termos</h2>
          <p className="text-sm text-slate-300 leading-relaxed">
            Ao utilizar o Clonify AI, você concorda integralmente com estes Termos de Uso. Se você não concorda com qualquer um dos termos aqui descritos, não utilize o serviço.
          </p>
        </section>

        <section className="space-y-2">
          <h2 className="text-lg font-semibold text-indigo-400">2. Descrição do Serviço</h2>
          <p className="text-sm text-slate-300 leading-relaxed">
            O Clonify AI é uma plataforma de automação que permite aos usuários clonar Reels do Instagram utilizando vídeos locais como fonte, com sobreposição de texto via IA (Gemini/OpenRouter), renderização via FFmpeg, e publicação automática através da Meta Graph API.
          </p>
        </section>

        <section className="space-y-2">
          <h2 className="text-lg font-semibold text-indigo-400">3. Uso Aceitável</h2>
          <ul className="text-sm text-slate-300 list-disc list-inside space-y-1">
            <li>Você é responsável pelo conteúdo dos vídeos que envia e clona.</li>
            <li>Não utilize o serviço para clonar conteúdo protegido por direitos autorais sem autorização.</li>
            <li>Não utilize o serviço para spam, fraude ou qualquer atividade ilegal.</li>
            <li>Você concorda em respeitar os Termos de Uso do Instagram e da Meta.</li>
          </ul>
        </section>

        <section className="space-y-2">
          <h2 className="text-lg font-semibold text-indigo-400">4. Automação e Postagem</h2>
          <p className="text-sm text-slate-300 leading-relaxed">
            O serviço utiliza a Meta Graph API oficial para publicação de Reels. Você é responsável por manter suas credenciais e tokens de acesso seguros. O serviço não se responsabiliza por bloqueios de conta decorrentes de uso indevido.
          </p>
        </section>

        <section className="space-y-2">
          <h2 className="text-lg font-semibold text-indigo-400">5. Limitação de Responsabilidade</h2>
          <p className="text-sm text-slate-300 leading-relaxed">
            O serviço é fornecido "como está", sem garantias de qualquer tipo. Não nos responsabilizamos por perda de dados, interrupções de serviço ou bloqueios de conta do Instagram decorrentes do uso da plataforma.
          </p>
        </section>

        <section className="space-y-2">
          <h2 className="text-lg font-semibold text-indigo-400">6. Encerramento de Conta</h2>
          <p className="text-sm text-slate-300 leading-relaxed">
            Reservamos o direito de suspender ou encerrar contas que violem estes Termos de Uso. Você pode solicitar a exclusão da sua conta e dados a qualquer momento através da nossa <a href="/data-deletion" className="text-indigo-400 underline">página de exclusão de dados</a>.
          </p>
        </section>
      </div>
    </div>
  )
}
