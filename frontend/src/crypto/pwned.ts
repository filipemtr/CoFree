/** k-Anonymity password check: no plaintext/full digest is transmitted or persisted. */
export async function pwnedPassword(password: string): Promise<{count:number;available:boolean}> {
  if (!password) throw new Error('Informe uma senha antes de verificar.');
  const digest = new Uint8Array(await crypto.subtle.digest('SHA-1',new TextEncoder().encode(password)));
  const hash = Array.from(digest, b=>b.toString(16).padStart(2,'0')).join('').toUpperCase();
  const prefix=hash.slice(0,5), suffix=hash.slice(5);
  let res: Response;
  try {res=await fetch(`https://api.pwnedpasswords.com/range/${prefix}`,{
    method:'GET',headers:{'Add-Padding':'true'},cache:'no-store'
  });}
  catch {throw new Error('Não foi possível consultar o serviço de senhas vazadas. Tente novamente.');}
  if (!res.ok) throw new Error('Serviço de verificação de senhas temporariamente indisponível.');
  const response=await res.text();
  const entry=response.split(/\r?\n/).find(line=>line.slice(0,35).toUpperCase()===suffix && line[35]===':');
  const count=entry?Number(entry.slice(36).trim()):0;
  if (!Number.isFinite(count)||count<0)throw new Error('Resposta inválida do serviço de verificação.');
  return {count,available:true};
}
