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
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
      </head>
      <body className="antialiased bg-[#0b0e17] text-slate-100 min-h-screen font-sans">
        {children}
      </body>
    </html>
  )
}
