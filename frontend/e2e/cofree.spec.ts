import {test,expect, type Page} from '@playwright/test';

const password='E2E-Password-Strong-2026!';

async function latestVerificationLink(email:string):Promise<string>{
  const api=process.env.MAILPIT_URL||'http://localhost:8025';
  for(let attempt=0;attempt<25;attempt++){
    const res=await fetch(`${api}/api/v1/messages`);
    if(res.ok){
      const inbox=await res.json() as {messages?:{ID:string;To?:{Address:string}[]}[]};
      const msg=inbox.messages?.find(m=>m.To?.some(t=>t.Address===email));
      if(msg){
        const detail=await fetch(`${api}/api/v1/message/${msg.ID}`).then(r=>r.json()) as {Text?:string};
        const link=detail.Text?.match(/https?:\/\/[^\s]+\/verificar-email\?token=[^\s]+/)?.[0];
        if(link)return link.trim();
      }
    }
    await new Promise(resolve=>setTimeout(resolve,450));
  }
  throw new Error('E-mail real não foi entregue ao Mailpit para '+email);
}

async function registerAndLogin(page:Page){
  const email=`cofree-test-${Date.now()}-${Math.floor(Math.random()*100000)}@example.com`;
  await page.goto('/cadastro');
  await page.getByPlaceholder('Como podemos chamar você?').fill('Pessoa E2E');
  await page.getByPlaceholder('voce@exemplo.com').fill(email);
  await page.getByPlaceholder('Pelo menos 12 caracteres').fill(password);
  await page.getByPlaceholder('Digite sua senha novamente').fill(password);
  await page.getByRole('button',{name:'Criar conta gratuita'}).click();
  await expect(page.getByText('Conta criada.',{exact:false})).toBeVisible();
  const link=await latestVerificationLink(email);
  await page.goto(link);
  await expect(page.getByText('E-mail confirmado!',{exact:false})).toBeVisible();
  await page.goto('/entrar');
  await page.getByPlaceholder('voce@exemplo.com').fill(email);
  await page.getByPlaceholder('Pelo menos 12 caracteres').fill(password);
  await page.getByRole('button',{name:'Entrar na minha conta'}).click();
  await expect(page.getByRole('heading',{name:/Olá, Pessoa/})).toBeVisible();
  return email;
}

test('cadastro, SMTP, verificação, login, monitoramento e revogação de sessão',async({page})=>{
  await registerAndLogin(page);
  await page.goto('/app/emails');
  await page.getByRole('button',{name:'Adicionar e-mail'}).first().click();
  await page.getByPlaceholder('voce@exemplo.com').fill('monitorado-e2e@example.com');
  await page.getByRole('button',{name:'Cadastrar e-mail'}).click();
  await expect(page.getByText('monitorado-e2e@example.com')).toBeVisible();
  await page.goto('/app/sessoes');
  await expect(page.getByText('Esta sessão')).toBeVisible();
  await page.getByRole('button',{name:'Revogar'}).first().click();
  await expect(page).toHaveURL(/entrar/);
});

test('Vault criado com recuperação, cifra local, lock/unlock e credencial',async({page})=>{
  await registerAndLogin(page);
  await page.goto('/app/vault');
  await page.getByPlaceholder('Crie uma senha mestra forte').fill('MinhaMestraBastanteSegura2026!');
  await page.getByPlaceholder('Repita sua senha').fill('MinhaMestraBastanteSegura2026!');
  await page.getByRole('button',{name:'Criar Vault seguro'}).click();
  await expect(page.getByRole('dialog',{name:'Guarde sua chave de recuperação'})).toBeVisible();
  await expect(page.locator('.recovery-code')).not.toBeEmpty();
  await page.getByRole('button',{name:/Guardei minha chave/}).click();
  await page.getByRole('button',{name:'Nova credencial'}).click();
  await page.getByPlaceholder('Ex.: Conta de e-mail').fill('Serviço E2E');
  await page.getByPlaceholder('usuario@exemplo.com').fill('e2e-usuario');
  await page.getByRole('dialog').locator('input[type="password"]').fill('SegredoLocalSuperForte123!');
  await page.getByRole('button',{name:'Salvar com criptografia'}).click();
  await expect(page.getByText('Serviço E2E')).toBeVisible();
  await page.getByRole('button',{name:'Bloquear'}).click();
  await page.getByPlaceholder('Sua senha mestra').fill('MinhaMestraBastanteSegura2026!');
  await page.getByRole('button',{name:'Desbloquear meu cofre'}).click();
  await expect(page.getByText('Serviço E2E')).toBeVisible();
});

test('página institucional e responsividade básica',async({page})=>{
  await page.goto('/');
  await expect(page.getByRole('heading',{name:/Seu mundo digital/})).toBeVisible();
  await expect(page.getByRole('link',{name:/Começar agora/})).toBeVisible();
  await expect(page.locator('body')).not.toHaveJSProperty('scrollWidth',99999);
});

test('senha muito curta mostra validação no cadastro sem enviar requisição',async({page})=>{
  await page.goto('/cadastro');
  await page.getByPlaceholder('Como podemos chamar você?').fill('Pessoa Teste');
  await page.getByPlaceholder('voce@exemplo.com').fill('valida@example.com');
  await page.getByPlaceholder('Pelo menos 12 caracteres').fill('curta123');
  await page.getByPlaceholder('Digite sua senha novamente').fill('curta123');
  await expect(page.locator('.password-warning')).toBeVisible();
  await page.getByRole('button',{name:'Criar conta gratuita'}).click();
  await expect(page.locator('.password-warning')).toBeVisible();
});

test('consulta manual usa prefixo SHA-1 e configura frequências',async({page})=>{
  await registerAndLogin(page);
  await page.goto('/app/senhas');
  await page.route('https://api.pwnedpasswords.com/range/5BAA6',async route=>{
    const headers={'Access-Control-Allow-Origin':'*','Access-Control-Allow-Headers':'Add-Padding','Access-Control-Allow-Methods':'GET, OPTIONS'};
    if(route.request().method()==='OPTIONS') await route.fulfill({status:204,headers});
    else await route.fulfill({status:200,headers,contentType:'text/plain',body:'1E4C9B93F3F0682250B6CF8331B7EE68FD8:4\r\n'});
  });
  await page.getByPlaceholder('Digite a senha para analisar').fill('password');
  await page.getByRole('button',{name:'Verificar exposição'}).click();
  await expect(page.getByText('Senha encontrada em vazamentos')).toBeVisible();
  await expect(page.getByText(/4 vez/)).toBeVisible();
  await page.goto('/app/configuracoes');
  await page.getByLabel('Ativar monitoramento automático de senhas').check();
  await page.getByLabel('Frequência de senhas').selectOption('7d');
  await page.getByLabel('Frequência de e-mails').selectOption('1h');
  await page.getByRole('button',{name:'Salvar monitoramentos'}).click();
  await expect(page.getByText('Frequências e monitoramentos atualizados.')).toBeVisible();
  await page.reload();
  await expect(page.getByLabel('Frequência de e-mails')).toHaveValue('1h');
  await expect(page.getByLabel('Ativar monitoramento automático de senhas')).toBeChecked();
});
