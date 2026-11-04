import assert from 'node:assert/strict';
import test from 'node:test';
import { pwnedPassword } from '../src/crypto/pwned.ts';

test('sends only a five-character SHA-1 prefix and returns an exposed count',async()=>{
  let called='';
  const original=globalThis.fetch;
  globalThis.fetch=async(url,opts)=>{
    called=url;
    assert.equal(opts.headers['Add-Padding'],'true');
    assert.equal(opts.cache,'no-store');
    return new Response('1E4C9B93F3F0682250B6CF8331B7EE68FD8:12345\r\nAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA:0\r\n');
  };
  try{
    const result=await pwnedPassword('password');
    assert.deepEqual(result,{count:12345,available:true});
    assert.equal(called,'https://api.pwnedpasswords.com/range/5BAA6');
    assert.ok(!new URL(called).pathname.includes('password'));
  }finally{globalThis.fetch=original;}
});

test('treats a nonmatch as zero without false safety guarantee',async()=>{
  const original=globalThis.fetch;
  globalThis.fetch=async()=>new Response('AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA:0');
  try {assert.equal((await pwnedPassword('not-an-obvious-password')).count,0);}
  finally {globalThis.fetch=original;}
});

test('handles unavailable provider without leaking the password',async()=>{
  const original=globalThis.fetch;
  globalThis.fetch=async()=>new Response('upstream failed',{status:503});
  try {await assert.rejects(()=>pwnedPassword('secret-to-never-log'),/temporariamente indisponível/);}
  finally {globalThis.fetch=original;}
});
