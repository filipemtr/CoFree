import sodium from 'libsodium-wrappers-sumo';
import type {SecretEntry, VaultCiphertext, VaultConfig} from '../lib/api';

const te = new TextEncoder();
const td = new TextDecoder();
const random = (n: number) => crypto.getRandomValues(new Uint8Array(n));
export const to64 = (a: Uint8Array): string => btoa(Array.from(a, b=>String.fromCharCode(b)).join(''));
export const from64 = (s: string): Uint8Array => Uint8Array.from(atob(s), c=>c.charCodeAt(0));
const keyFromBytes = (b:Uint8Array) => crypto.subtle.importKey('raw', b as BufferSource, 'AES-GCM',false,['encrypt','decrypt']);
async function seal(bytes: Uint8Array, key: Uint8Array): Promise<string> {
  const iv=random(12), k=await keyFromBytes(key);
  const cipher = new Uint8Array(await crypto.subtle.encrypt({name:'AES-GCM',iv:iv as BufferSource}, k, bytes as BufferSource));
  const packed = new Uint8Array(iv.length+cipher.length); packed.set(iv); packed.set(cipher,iv.length);
  return to64(packed);
}
async function open(encoded: string, key: Uint8Array): Promise<Uint8Array> {
  const packed=from64(encoded);if (packed.length < 29) throw Error('Pacote criptografado inválido');
  const k=await keyFromBytes(key);
  return new Uint8Array(await crypto.subtle.decrypt({name:'AES-GCM',iv:packed.slice(0,12) as BufferSource},k,packed.slice(12) as BufferSource));
}
async function passwordKey(password:string,salt:Uint8Array,iterations:number,memory_kib:number):Promise<Uint8Array> {
  await sodium.ready;
  return sodium.crypto_pwhash(32,password,salt,iterations,memory_kib*1024,sodium.crypto_pwhash_ALG_ARGON2ID13);
}
async function recoveryKey(code:string,salt:Uint8Array):Promise<Uint8Array> {
  const input=from64(code); if(input.length!==32)throw Error('Chave de recuperação inválida');
  const base=await crypto.subtle.importKey('raw',input as BufferSource,'HKDF',false,['deriveBits']);
  const bits=await crypto.subtle.deriveBits({name:'HKDF',hash:'SHA-256',salt:salt as BufferSource, info:te.encode('CoFree recovery v1')},base,256);
  return new Uint8Array(bits);
}
export async function createVault(password:string):Promise<{config:VaultConfig; recoveryCode:string; vaultKey:Uint8Array}> {
  if(password.length<12)throw Error('A senha mestra precisa ter pelo menos 12 caracteres');
  const salt=random(16),recoverySalt=random(16),code=to64(random(32)),vaultKey=random(32);
  const iterations=3,memory_kib=65536;
  const passKey=await passwordKey(password,salt,iterations,memory_kib);
  const wrapped_key=await seal(vaultKey,passKey);
  const recovery_wrapped_key=await seal(vaultKey,await recoveryKey(code,recoverySalt));
  passKey.fill(0);
  return {config:{salt:to64(salt),iterations,memory_kib,wrapped_key,recovery_wrapped_key,recovery_salt:to64(recoverySalt),version:1},recoveryCode:code,vaultKey};
}
export async function unlockVault(config:VaultConfig, password:string):Promise<Uint8Array> {
  const passKey=await passwordKey(password,from64(config.salt),config.iterations,config.memory_kib);
  try {return await open(config.wrapped_key,passKey);} finally {passKey.fill(0);}
}
export async function recoverVault(config:VaultConfig,code:string):Promise<Uint8Array> {
  const derived=await recoveryKey(code,from64(config.recovery_salt));
  try {return await open(config.recovery_wrapped_key,derived);} finally{derived.fill(0);}
}
export async function rewrapVault(config:VaultConfig,vaultKey:Uint8Array,newPassword:string,recoveryCode?:string):Promise<VaultConfig> {
  const salt=random(16), iterations=3, memory_kib=65536;
  const derived=await passwordKey(newPassword,salt,iterations,memory_kib);
  const wrapped_key=await seal(vaultKey,derived);derived.fill(0);
  if(!recoveryCode)return {...config,salt:to64(salt),iterations,memory_kib,wrapped_key};
  const recovery_salt=random(16);
  return {...config,salt:to64(salt),iterations,memory_kib,wrapped_key,recovery_salt:to64(recovery_salt),
    recovery_wrapped_key:await seal(vaultKey,await recoveryKey(recoveryCode,recovery_salt))};
}
export async function encryptItem(item:SecretEntry,key:Uint8Array,id:string,userId:string):Promise<{id:string;nonce:string;ciphertext:string}> {
  const iv=random(12),cipher=await crypto.subtle.encrypt({name:'AES-GCM',iv:iv as BufferSource,additionalData:te.encode(`cofree:v1:${userId}:${id}`) as BufferSource},await keyFromBytes(key),te.encode(JSON.stringify(item)) as BufferSource);
  return {id,nonce:to64(iv),ciphertext:to64(new Uint8Array(cipher))};
}
export async function decryptItem(item:VaultCiphertext,key:Uint8Array,userId:string):Promise<SecretEntry> {
  const plain=await crypto.subtle.decrypt({name:'AES-GCM',iv:from64(item.nonce) as BufferSource,additionalData:te.encode(`cofree:v1:${userId}:${item.id}`) as BufferSource},await keyFromBytes(key),from64(item.ciphertext) as BufferSource);
  return JSON.parse(td.decode(plain)) as SecretEntry;
}
export function generatePassword(length=20):string {
  const chars='ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789!@#$%&*_-';
  // Rejection sampling eliminates modulo bias.
  let result='';const cap=Math.floor(256/chars.length)*chars.length;
  while(result.length<length){for(const b of random(length*2)){if(b<cap){result+=chars[b%chars.length];if(result.length===length)break;}}}
  return result;
}
export {pwnedPassword} from './pwned';
