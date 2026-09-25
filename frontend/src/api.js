const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? ''

export async function getHealth() {
  const response = await fetch(`${API_BASE_URL}/api/health`)

  if (!response.ok) {
    throw new Error('Não foi possível conectar ao backend.')
  }

  return response.json()
}

export class ApiError extends Error {
  constructor(message, status, payload = null) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.payload = payload
  }
}

export async function uploadDataset(files) {
  const body = new FormData()
  for (const file of files) {
    body.append('files', file, file.name)
  }

  const response = await fetch(`${API_BASE_URL}/api/datasets`, {
    method: 'POST',
    body,
  })
  const payload = await response.json().catch(() => null)

  if (!response.ok) {
    throw new ApiError(
      payload?.errors?.[0]?.message ?? 'Não foi possível validar o pacote.',
      response.status,
      payload,
    )
  }

  return payload
}
