import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {createRequire} from 'node:module';
import http from 'node:http';
const require=createRequire(import.meta.url);
const server=require('../scripts/serve-professional-portals.cjs');

test('only three professional login entry points and E54 activation are public', async()=>{
  await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
  const port=server.address().port;
  const get=(path,headers={})=>fetch('http://127.0.0.1:'+port+path,{headers});
  try{
    for(const route of ['/superadmin','/etablissement','/entreprise']){
      const result=await get(route);
      assert.equal(result.status,200,route);
      assert.match(result.headers.get('content-type'),/text\/html/);
      // The local Node server advertises its same-origin API proxy.
      // This avoids browser cookie isolation across different ports.
      assert.match(await result.text(), /<meta name="gconnect-api-base" content="\/api\/v1">/);
    }
    // E54 activation is a deliberately public HTML entry point, never an admin frame.
    const activation=await get('/entreprise-activation.html');
    assert.equal(activation.status,200);
    assert.match(activation.headers.get('content-type'),/text\/html/);
    assert.equal(activation.headers.get('cache-control'),'no-store');
    assert.equal(activation.headers.get('referrer-policy'),'no-referrer');
    const markup=await activation.text();
    assert.match(markup,/gconnect-api-base" content="\/api\/v1"/);
    assert.match(markup,/id="ea-form"/);
    assert.match(markup,/href="\/entreprise#login\/entreprise"/);
    assert.match(markup,/name="robots" content="noindex,nofollow"/);
    assert.equal((await get('/entreprise-activation.html.backup')).status,404);
    // All professional roles render the same approved photo-backed login shell.
    const pages=await Promise.all(['/superadmin','/etablissement','/entreprise']
      .map(async route=>(await get(route)).text()));
    assert.equal(pages[0],pages[1]);
    assert.equal(pages[1],pages[2]);
    for(const legacy of ['/','/index.html','/auth.html','/admin-login-e19.html',
      '/admin-connected-e19.html','/etablissement.html','/etablissement-connexion.html',
      '/superadmin-login.html','/superadmin-connected-e18.html','/superadmin-preview.html',
      '/entreprise.html','/etablissement-activation.html']){
      const result=await get(legacy);
      assert.equal(result.status,404,legacy);
    }
    assert.equal((await get('/_internal/admin-console')).status,404);
    assert.equal((await get('/_internal/admin-console',{'Sec-Fetch-Dest':'iframe'})).status,200);
    assert.equal((await get('/glass.css')).status,200);
    assert.equal((await get('/etablissement-api.js')).status,200);
    assert.equal((await get('/assets/logo_icon.png')).status,200);
    assert.equal((await get('/%2e%2e/package.json')).status,404);
  }finally{
    await new Promise((resolve,reject)=>server.close(error=>error?reject(error):resolve()));
  }
});


test('local session resume uses the same site for UI and API',()=>{
  const client=readFileSync(new URL('../dist/etablissement-api.js',import.meta.url),'utf8');
  const serverCode=readFileSync(new URL('../scripts/serve-professional-portals.cjs',import.meta.url),'utf8');
  assert.match(client,/':8002\/api\/v1'/);
  assert.match(client,/window\.location\.hostname \+ ':8002\/api\/v1'/);
  assert.match(serverCode,/content="\/api\/v1"/);
  assert.match(serverCode,/if\(pathname\.startsWith\('\/api\/v1\/'\)\)return proxyApi/);
  assert.match(client,/\['\/users\/web-mfa\/verify\/', '\/users\/web-resume\/', '\/users\/web-logout\/'\]/);
  assert.match(client,/credentials:\s*\(path\.startsWith/);
});


test('each privileged portal restores only its own verified role',()=>{
  const auth=readFileSync(new URL('../dist/auth-shared-e19.js',import.meta.url),'utf8');
  const api=readFileSync(new URL('../dist/etablissement-api.js',import.meta.url),'utf8');
  assert.match(auth,/\['\/superadmin','\/etablissement','\/entreprise','\/admin-login-e19\.html'\]/);
  assert.match(auth,/api\.restoreSession\(expectedRole\)/);
  assert.match(api,/request\('\/users\/web-resume\/', 'POST', \{ role \}\)/);
  assert.match(api,/data\.role !== role/);
});



test('local proxy preserves HttpOnly MFA cookie and resumes on the same browser origin',async()=>{
  let seenCookie='',seenOrigin='';
  const django=http.createServer(async(req,res)=>{
    seenOrigin=req.headers.origin||'';
    if(req.url==='/api/v1/users/web-mfa/verify/'){
      assert.equal(req.method,'POST');
      res.writeHead(200,{
        'Content-Type':'application/json',
        'Set-Cookie':'gconnect_web_session_superadmin=test-device; Max-Age=3600; Path=/api/v1/users/; HttpOnly; SameSite=Lax'
      });
      res.end(JSON.stringify({success:true,data:{role:'superAdmin'}}));
    }else if(req.url==='/api/v1/users/web-resume/'){
      seenCookie=req.headers.cookie||'';
      res.writeHead(seenCookie.includes('gconnect_web_session_superadmin=test-device')?200:401,{'Content-Type':'application/json'});
      res.end(JSON.stringify({success:Boolean(seenCookie),data:{role:'superAdmin'}}));
    }else{
      res.writeHead(404);res.end();
    }
  });
  await new Promise(resolve=>django.listen(0,'127.0.0.1',resolve));
  process.env.GCONNECT_BACKEND_PORT=String(django.address().port);
  await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
  const origin='http://127.0.0.1:'+server.address().port;
  try{
    const verify=await fetch(origin+'/api/v1/users/web-mfa/verify/',{
      method:'POST',headers:{Origin:origin,'Content-Type':'application/json'},
      body:JSON.stringify({challenge:'demo',code:'123456'})
    });
    assert.equal(verify.status,200);
    const setCookie=verify.headers.get('set-cookie')||'';
    assert.match(setCookie,/HttpOnly/);
    assert.match(setCookie,/Path=\/api\/v1\/users\//);
    const resume=await fetch(origin+'/api/v1/users/web-resume/',{
      method:'POST',
      headers:{Origin:origin,Cookie:setCookie.split(';')[0],'Content-Type':'application/json'},
      body:JSON.stringify({role:'superAdmin'})
    });
    assert.equal(resume.status,200);
    assert.equal((await resume.json()).data.role,'superAdmin');
    assert.match(seenCookie,/gconnect_web_session_superadmin=test-device/);
    assert.equal(seenOrigin,origin);
  }finally{
    delete process.env.GCONNECT_BACKEND_PORT;
    await new Promise(resolve=>server.close(resolve));
    await new Promise(resolve=>django.close(resolve));
  }
});
