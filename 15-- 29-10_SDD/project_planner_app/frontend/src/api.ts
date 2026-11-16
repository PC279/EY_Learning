const API_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000'

export function setToken(token: string | null) {
  if (token) localStorage.setItem('daymark_token', token)
  else localStorage.removeItem('daymark_token')
}
export function getToken() { return localStorage.getItem('daymark_token') }

export async function api<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getToken()
  const headers = new Headers(options.headers)
  if (options.body && !headers.has('Content-Type')) headers.set('Content-Type', 'application/json')
  if (token) headers.set('Authorization', `Bearer ${token}`)
  const response = await fetch(`${API_URL}${path}`, { ...options, headers })
  const text = await response.text()
  let payload: any = null
  try { payload = text ? JSON.parse(text) : null } catch { payload = { detail: text } }
  if (!response.ok) {
    if (response.status === 401) setToken(null)
    throw new Error(payload?.detail || `Request failed (${response.status})`)
  }
  return payload as T
}
