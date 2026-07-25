import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'Clonify AI - Automação e Clonagem Inteligente de Reels',
  description: 'Plataforma para automação e clonagem de Reels do Instagram',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="pt-BR">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
      </head>
      <body className="antialiased bg-slate-50 text-slate-900 min-h-screen font-sans">
        {children}
      </body>
    </html>
  )
}
