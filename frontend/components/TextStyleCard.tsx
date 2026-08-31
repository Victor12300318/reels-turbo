'use client'

import { useEffect, useState } from 'react'
import { Type } from 'lucide-react'

export interface TextStyleValue {
  font: string
  color: string
  background: 'none' | 'white' | 'black'
}

interface FontOption {
  id: string
  label: string
  css_family: string
}

interface ColorOption {
  id: string
  label: string
  hex: string
}

interface BackgroundOption {
  id: 'none' | 'white' | 'black'
  label: string
}

export interface TextStyleOptions {
  fonts: FontOption[]
  colors: ColorOption[]
  backgrounds: BackgroundOption[]
}

interface TextStyleCardProps {
  value: TextStyleValue
  options: TextStyleOptions
  saving: boolean
  message: string
  onChange: (value: TextStyleValue) => void
  onSave: () => void
}

function isValidHex(value: string) {
  return /^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$/.test(value)
}

function normalizeHex(value: string) {
  if (!value.startsWith('#')) {
    value = `#${value}`
  }
  if (value.length === 4) {
    return `#${value[1]}${value[1]}${value[2]}${value[2]}${value[3]}${value[3]}`
  }
  return value.toLowerCase()
}

function hexToRgb(value: string) {
  const hex = normalizeHex(value)
  return {
    r: parseInt(hex.slice(1, 3), 16),
    g: parseInt(hex.slice(3, 5), 16),
    b: parseInt(hex.slice(5, 7), 16),
  }
}

function relativeLuminance(value: string) {
  const { r, g, b } = hexToRgb(value)
  const adjust = (channel: number) => {
    const ratio = channel / 255
    return ratio <= 0.03928 ? ratio / 12.92 : ((ratio + 0.055) / 1.055) ** 2.4
  }
  return 0.2126 * adjust(r) + 0.7152 * adjust(g) + 0.0722 * adjust(b)
}

function contrastRatio(first: string, second: string) {
  const firstLuminance = relativeLuminance(first)
  const secondLuminance = relativeLuminance(second)
  const lighter = Math.max(firstLuminance, secondLuminance)
  const darker = Math.min(firstLuminance, secondLuminance)
  return (lighter + 0.05) / (darker + 0.05)
}

export default function TextStyleCard({
  value,
  options,
  saving,
  message,
  onChange,
  onSave
}: TextStyleCardProps) {
  const [customColor, setCustomColor] = useState(value.color.startsWith('#') ? value.color : '#0066FF')

  useEffect(() => {
    if (value.color.startsWith('#')) {
      setCustomColor(value.color)
    }
  }, [value.color])

  const selectedFont = options.fonts.find(font => font.id === value.font) || options.fonts[0]
  const selectedPreset = value.color.startsWith('#') ? 'custom' : value.color
  const selectedColor = value.color.startsWith('#')
    ? value.color
    : options.colors.find(color => color.id === value.color)?.hex || '#FFFFFF'

  const previewStyle: React.CSSProperties = {
    fontFamily: selectedFont?.css_family || 'system-ui',
    color: selectedColor,
    background: value.background === 'white' ? 'rgba(255,255,255,0.92)' : value.background === 'black' ? 'rgba(0,0,0,0.72)' : 'transparent',
    textShadow: value.background === 'none' ? '0 2px 8px rgba(0,0,0,0.65)' : 'none',
  }

  const backgroundHex = value.background === 'white' ? '#FFFFFF' : value.background === 'black' ? '#000000' : null
  const contrast = backgroundHex ? contrastRatio(selectedColor, backgroundHex) : null
  const lowContrast = contrast !== null && contrast < 3
  const canSave = !saving && !lowContrast && (!value.color.startsWith('#') || isValidHex(value.color))

  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-6 space-y-5 shadow-sm hover:shadow-md transition-all">
      <header className="border-b border-slate-100 pb-3">
        <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
          <Type className="w-4 h-4 text-[#0066FF]" /> Estilo do Texto
        </h3>
        <p className="text-[11px] text-slate-500 mt-1">
          Fonte, cor e fundo usados nos próximos vídeos. Posição e tamanho continuam automáticos pela zona segura.
        </p>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-[1.1fr_0.9fr] gap-5">
        <div className="space-y-4">
          <div className="space-y-2">
            <label className="text-xs font-semibold text-slate-700">Fonte</label>
            <select
              value={value.font}
              onChange={(event) => onChange({ ...value, font: event.target.value })}
              className="w-full rounded-xl border border-slate-200 bg-slate-50 px-3.5 py-2.5 text-xs text-slate-900 focus:border-[#0066FF] focus:bg-white focus:outline-none transition-all"
            >
              {options.fonts.map(font => (
                <option key={font.id} value={font.id}>{font.label}</option>
              ))}
            </select>
          </div>

          <div className="space-y-2">
            <label className="text-xs font-semibold text-slate-700">Cor do texto</label>
            <select
              value={selectedPreset}
              onChange={(event) => {
                if (event.target.value === 'custom') {
                  onChange({ ...value, color: customColor })
                } else {
                  onChange({ ...value, color: event.target.value })
                }
              }}
              className="w-full rounded-xl border border-slate-200 bg-slate-50 px-3.5 py-2.5 text-xs text-slate-900 focus:border-[#0066FF] focus:bg-white focus:outline-none transition-all"
            >
              {options.colors.map(color => (
                <option key={color.id} value={color.id}>{color.label}</option>
              ))}
              <option value="custom">Cor personalizada</option>
            </select>

            {selectedPreset === 'custom' && (
              <div className="flex items-center gap-2">
                <input
                  type="color"
                  value={isValidHex(customColor) ? normalizeHex(customColor) : '#0066FF'}
                  onChange={(event) => {
                    setCustomColor(event.target.value)
                    onChange({ ...value, color: event.target.value })
                  }}
                  className="h-10 w-14 cursor-pointer rounded-xl border border-slate-200 bg-slate-50"
                />
                <input
                  type="text"
                  value={customColor}
                  onChange={(event) => {
                    setCustomColor(event.target.value)
                    if (isValidHex(event.target.value)) {
                      onChange({ ...value, color: normalizeHex(event.target.value) })
                    }
                  }}
                  placeholder="#0066FF"
                  className="flex-1 rounded-xl border border-slate-200 bg-slate-50 px-3.5 py-2.5 text-xs font-mono text-slate-900 focus:border-[#0066FF] focus:bg-white focus:outline-none"
                />
              </div>
            )}
          </div>

          <div className="space-y-2">
            <label className="text-xs font-semibold text-slate-700">Fundo do texto</label>
            <select
              value={value.background}
              onChange={(event) => onChange({ ...value, background: event.target.value as TextStyleValue['background'] })}
              className="w-full rounded-xl border border-slate-200 bg-slate-50 px-3.5 py-2.5 text-xs text-slate-900 focus:border-[#0066FF] focus:bg-white focus:outline-none transition-all"
            >
              {options.backgrounds.map(background => (
                <option key={background.id} value={background.id}>{background.label}</option>
              ))}
            </select>
          </div>
        </div>

        <div className="space-y-3">
          <p className="text-xs font-semibold text-slate-700">Pré-visualização</p>
          <div className="relative mx-auto aspect-[9/16] w-full max-w-[220px] overflow-hidden rounded-2xl border border-slate-200 bg-gradient-to-br from-slate-900 via-slate-700 to-slate-900">
            <div className="absolute inset-0 flex items-end justify-center p-5">
              <p
                className="max-w-full rounded-xl px-3 py-2 text-center text-lg font-bold leading-snug"
                style={previewStyle}
              >
                Seu texto aparece aqui
              </p>
            </div>
          </div>
          {lowContrast && (
            <p className="rounded-xl border border-amber-200 bg-amber-50 p-3 text-[11px] font-semibold text-amber-800">
              Contraste muito baixo. Escolha outra cor ou outro fundo.
            </p>
          )}
        </div>
      </div>

      {message && (
        <p className="text-xs text-blue-800 bg-blue-50 p-3 rounded-xl border border-blue-200">{message}</p>
      )}

      <button
        type="button"
        onClick={onSave}
        disabled={!canSave}
        className="w-full rounded-xl bg-[#0066FF] py-3 text-xs font-bold text-white shadow-sm shadow-blue-600/20 transition-all hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
      >
        {saving ? 'Salvando...' : 'Salvar Estilo do Texto'}
      </button>
    </section>
  )
}
