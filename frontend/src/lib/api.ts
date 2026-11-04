import {errorMessage} from './errors';
export class ApiError extends Error {constructor(public code: number, message: string) { super(message); }}
export function csrfToken(): string {return decodeURIComponent(document.cookie.split('; ').find(v => v.startsWith('cofree_csrf='))?.split('=').slice(1).join('=') || '');}
export async function api<T>(url: string, options: RequestInit = {}): Promise<T> {
  const method = options.method || 'GET';
  const headers: Record<string, string> = {'Content-Type':'application/json', ...(options.headers as Record<string,string> || {})};
  if (!['GET','HEAD','OPTIONS'].includes(method.toUpperCase()) && csrfToken()) headers['X-CSRF-Token'] = csrfToken();
  let res: Response;
  try {res = await fetch(`/api${url}`, {...options, method, headers, credentials:'same-origin'});}
  catch {throw new ApiError(0, 'Não foi possível conectar ao servidor. Verifique sua conexão.');}
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new ApiError(res.status, errorMessage(data, res.status));
  return data as T;
}
export type MonitoringPreferences = {email_enabled:boolean;email_interval:'1h'|'24h'|'7d'|'30d';password_enabled:boolean;password_interval:'1h'|'24h'|'7d'|'30d'};
export type User = {id: string; email: string; name: string; verified: boolean; notify_exposures: boolean};
export type Monitor = {id:string; email:string; status:string; last_checked: string|null; next_check:string|null; created_at:string};
export type Notice = {id:string; title:string; message:string; read:boolean; created_at:string};
export type Dashboard = {monitored_emails:number; exposures:number; vault_items:number; pending_checks:number; email_health:{clear:number;exposed:number;pending:number;queued:number;unavailable:number}; emails:Monitor[]; notifications:Notice[]};
export type VaultConfig = {salt:string;iterations:number;memory_kib:number;wrapped_key:string;recovery_wrapped_key:string;recovery_salt:string;version:number};
export type VaultCiphertext = {id:string;ciphertext:string;nonce:string;created_at:string;updated_at:string};
export type SecretEntry = {name:string;username:string;password:string;website:string;notes:string;category:string;favorite:boolean};
