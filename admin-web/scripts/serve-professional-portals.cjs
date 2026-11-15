'use strict';
/* Local professional portal server. Public HTML entry points are deliberately limited.
 * This server controls routing, not authorization: Django WebToken/MFA remains mandatory. */
const http = require('node:http');
const fs = require('node:fs');
const path = require('node:path');

const root = path.resolve(__dirname, '../dist');
const port = Number(process.env.PORT || 5173);
// In local development, all Django requests pass through the same-origin
// portal proxy. The backend keeps MFA and revocable sessions authoritative.
let apiMeta = '<meta name="gconnect-api-base" content="/api/v1">';
if (process.env.GCONNECT_API_BASE_URL) {
  const apiUrl = new URL(process.env.GCONNECT_API_BASE_URL);
  if (apiUrl.protocol !== 'https:' &&
      !(apiUrl.protocol === 'http:' && ['localhost','127.0.0.1'].includes(apiUrl.hostname))) {
    throw new Error('Adresse du backend de développement non sécurisée.');
  }
  apiMeta = '<meta name="gconnect-api-base" content="' +
    apiUrl.href.replaceAll('&','&amp;').replaceAll('"','&quot;') + '">';
}
const routes = Object.freeze({
  '/superadmin': 'admin-login-e19.html',
  '/etablissement': 'admin-login-e19.html',
  '/entreprise': 'admin-login-e19.html',
  // E54: public single-use activation page; account activation is verified by Django.
  '/entreprise-activation.html': 'entreprise-activation.html',
  '/_internal/admin-console': 'admin-connected-e19.html',
});
const mime = {
  '.css':'text/css; charset=utf-8', '.js':'text/javascript; charset=utf-8',
  '.json':'application/json; charset=utf-8', '.png':'image/png',
  '.jpg':'image/jpeg', '.jpeg':'image/jpeg', '.webp':'image/webp',
  '.svg':'image/svg+xml', '.gif':'image/gif', '.ico':'image/x-icon',
  '.woff':'font/woff', '.woff2':'font/woff2', '.ttf':'font/ttf',
};
const respond=(res,status,message)=>{
  res.writeHead(status, {'Content-Type':'text/plain; charset=utf-8','Cache-Control':'no-store',
    'X-Content-Type-Options':'nosniff'});
  res.end(message);
};
const proxyApi=(req,res,url)=>{
  if(!['GET','HEAD','POST','PATCH','PUT','DELETE','OPTIONS'].includes(req.method))
    return respond(res,405,'Méthode non autorisée');
  const backendPort=Number(process.env.GCONNECT_BACKEND_PORT || 8002);
  if(!Number.isInteger(backendPort)||backendPort<1||backendPort>65535)
    return respond(res,500,'Port du backend invalide');
  // Never use an external Host header as the upstream target.
  const upstream=http.request({
    hostname:'127.0.0.1',port:backendPort,method:req.method,
    path:url.pathname+url.search,
    headers:{...req.headers,host:'127.0.0.1:'+backendPort},
  },response=>{
    res.writeHead(response.statusCode||502,{
      ...response.headers,'cache-control':'no-store',
    });
    response.pipe(res);
  });
  upstream.on('error',()=>{
    if(!res.headersSent){
      res.writeHead(502,{'Content-Type':'application/json; charset=utf-8','Cache-Control':'no-store'});
      res.end(JSON.stringify({success:false,message:'Le backend Django est indisponible.'}));
    }else res.destroy();
  });
  req.pipe(upstream);
};
const server=http.createServer((req,res)=>{
  let url;
  try{url=new URL(req.url,'http://localhost');}catch{return respond(res,400,'Adresse invalide');}
  let pathname;
  try{pathname=decodeURIComponent(url.pathname);}catch{return respond(res,400,'Adresse invalide');}
  if(pathname.includes('\\')||pathname.includes('\0')||pathname.split('/').includes('..'))
    return respond(res,404,'Page introuvable');
  if(pathname.startsWith('/api/v1/'))return proxyApi(req,res,url);
  if(!['GET','HEAD'].includes(req.method))return respond(res,405,'Méthode non autorisée');
  const html=Object.prototype.hasOwnProperty.call(routes,pathname);
  // Direct navigation to the internal frame is not a public portal.
  if(pathname==='/_internal/admin-console'&&req.headers['sec-fetch-dest']!=='iframe')
    return respond(res,404,'Page introuvable');
  const ext=path.extname(pathname).toLowerCase();
  const asset=!html && ext!=='.html' && Object.prototype.hasOwnProperty.call(mime,ext);
  if(!html&&!asset)return respond(res,404,'Page introuvable');
  const filename=html?routes[pathname]:pathname.slice(1);
  const target=path.resolve(root,filename);
  if(!target.startsWith(root+path.sep))return respond(res,404,'Page introuvable');
  fs.stat(target,(error,stat)=>{
    if(error||!stat.isFile())return respond(res,404,'Page introuvable');
    const headers={
      'Content-Type':html?'text/html; charset=utf-8':mime[ext],
      'X-Content-Type-Options':'nosniff',
      'Referrer-Policy':'no-referrer',
      'Cache-Control':html?'no-store':'public, max-age=300',
      'Content-Security-Policy':"frame-ancestors 'self'",
    };
    if(html){
      fs.readFile(target,'utf8',(readError,markup)=>{
        if(readError)return respond(res,500,'Lecture de la page impossible');
        const body=markup.replace(/<head([^>]*)>/i,match=>match+apiMeta);
        res.writeHead(200,headers);
        return res.end(req.method==='HEAD'?undefined:body);
      });
      return;
    }
    res.writeHead(200,headers);
    if(req.method==='HEAD')return res.end();
    const stream=fs.createReadStream(target);
    stream.on('error',()=>res.destroy());
    stream.pipe(res);
  });
});
if(require.main===module){
  server.listen(port,'127.0.0.1',()=>console.log('G-Connect professionnel : http://localhost:'+port+'/superadmin | /etablissement | /entreprise'));
}
module.exports=server;

