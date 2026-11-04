import assert from 'node:assert/strict';
import test from 'node:test';
import {errorMessage} from '../src/lib/errors.ts';

test('translates short password FastAPI 422 to Portuguese',()=>{
 const data={detail:[{type:'string_too_short',loc:['body','password'],ctx:{min_length:12}}]};
 assert.equal(errorMessage(data,422),'O campo senha deve conter pelo menos 12 caracteres.');
});
test('translates missing fields without reflecting potentially sensitive submitted values',()=>{
 assert.equal(errorMessage({detail:[{type:'missing',loc:['body','email'],input:'private'}]},422),'Preencha o campo e-mail.');
});
test('handles generic HTTP failures and plain API messages',()=>{
 assert.equal(errorMessage({detail:'E-mail já cadastrado'},409),'E-mail já cadastrado');
 assert.match(errorMessage({detail:[]},422),/Confira os campos/);
 assert.match(errorMessage({},500),/HTTP 500/);
});
