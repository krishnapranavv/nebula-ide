interface Props {
  modelUsed?: string
  tokensUsed?: number
}

export default function ProviderBadge({ modelUsed, tokensUsed }: Props) {
  if (!modelUsed) return null

  const isHaiku = modelUsed.includes('haiku')
  const label = isHaiku ? 'Haiku' : modelUsed.split('-').slice(1, 3).join(' ')

  return (
    <span className="inline-flex items-center gap-1.5 text-2xs font-mono px-2 py-0.5 rounded-full bg-ide-purple-dim text-ide-purple border border-ide-purple/30">
      <span className="w-1.5 h-1.5 rounded-full bg-ide-purple animate-pulse" />
      {label}
      {tokensUsed !== undefined && (
        <span className="text-ide-muted ml-0.5">{tokensUsed.toLocaleString()} tok</span>
      )}
    </span>
  )
}