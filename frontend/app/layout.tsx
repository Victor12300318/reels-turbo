import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'Reels Cloner AI',
  description: 'Plataforma para automação e clonagem de Reels do Instagram',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="pt-BR" className="dark">
      <body className="antialiased bg-[#090d16] text-slate-100 min-h-screen">
        {children}
      </body>
    </html>
  )
}
