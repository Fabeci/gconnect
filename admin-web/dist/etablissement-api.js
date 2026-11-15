'use strict';
/* G-Connect Establishment web API client — Sprint E1.
 * Shared auth and read-only establishment dashboard client. The JS bearer token
 * stays in this closure, never in localStorage/sessionStorage or the URL.
 * The backend may resume a verified device with an HttpOnly SameSite cookie.
 * Other features remain local previews until their permissions are audited.
 */
(function () {
  let token = null;
  let tokenKind = 'Token';
  let current = null;
  let generation = 0;

  function baseUrl() {
    const configured = window.GCONNECT_API_BASE_URL ||
      document.querySelector('meta[name="gconnect-api-base"]')?.getAttribute('content');
    if (configured) {
      const url = new URL(configured, window.location.href);
      if (url.protocol !== 'https:' &&
          !(url.protocol === 'http:' && ['localhost', '127.0.0.1'].includes(url.hostname))) {
        throw new Error('Adresse API non sécurisée.');
      }
      return url.href.replace(/\/+$/, '');
    }
    if (['localhost', '127.0.0.1'].includes(window.location.hostname)) {
      return window.location.protocol + '//' + window.location.hostname + ':8002/api/v1';
    }
    throw new Error('Adresse API non configurée pour cet environnement.');
  }

  async function request(path, method = 'GET', payload = null, authToken = null, scheme = tokenKind) {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 12000);
    const headers = { Accept: 'application/json' };
    const multipart = typeof FormData !== 'undefined' && payload instanceof FormData;
    if (payload !== null && !multipart) headers['Content-Type'] = 'application/json';
    if (authToken) headers.Authorization = scheme + ' ' + authToken;
    try {
      const response = await fetch(baseUrl() + path, {
        method,
        headers,
        body: payload === null ? undefined : multipart ? payload : JSON.stringify(payload),
        cache: 'no-store',
        credentials: (path.startsWith('/users/register/') ||
          ['/users/web-mfa/verify/', '/users/web-resume/', '/users/web-logout/'].includes(path))
          ? 'include' : 'omit',
        signal: controller.signal,
      });
      const json = await response.json().catch(() => null);
      if (!response.ok || !json || json.success !== true) {
        if (response.status === 401 && authToken) {
          throw new Error('Votre session a expiré. Reconnectez-vous.');
        }
        throw new Error(json?.message || (response.status === 429 ? 'Trop de tentatives. Patientez quelques minutes avant de réessayer.' : 'La demande au serveur a échoué.'));
      }
      return json.data;
    } catch (error) {
      if (error?.name === 'AbortError') {
        throw new Error('Le serveur ne répond pas. Réessayez dans un instant.');
      }
      if (error instanceof TypeError) {
        throw new Error('Connexion au serveur impossible. Vérifiez que le backend est démarré.');
      }
      throw error;
    } finally {
      clearTimeout(timeout);
    }
  }

  function disconnect() {
    generation += 1;
    token = null;
    tokenKind = 'Token';
    current = null;
  }

  async function refresh() {
    const version = generation;
    const sessionToken = token;
    if (!sessionToken) throw new Error('Veuillez vous connecter.');
    try {
      const profile = await request('/users/me/', 'GET', null, sessionToken);
      if (generation !== version || token !== sessionToken) {
        throw new Error('La session a été fermée.');
      }
      let stats;
      if (profile?.role === 'etablissement' && profile.institution_id) {
        stats = await request('/backoffice/stats/', 'GET', null, sessionToken);
        if (stats?.scope !== 'institution' || !stats.users || !stats.posts) {
          throw new Error('Statistiques de votre établissement indisponibles.');
        }
      } else if (profile?.role === 'enterprise' && profile.enterprise_id) {
        if (profile.enterprise_role === 'recruiter') {
          // E53 recruiters do not own the company. The E38 dashboard is owner-only.
          const scoped = await request('/users/enterprise/dashboard/', 'GET', null, sessionToken);
          if (scoped?.membership !== 'recruiter' ||
              scoped.company?.id !== profile.enterprise_id ||
              !Number.isSafeInteger(scoped.stats?.opportunities) ||
              !Number.isSafeInteger(scoped.stats?.applications)) {
            throw new Error('Périmètre Entreprise invalide.');
          }
          // Read-only counts only. No E38 billing/ownership features are unlocked.
          stats = {scope:'enterprise', enterprise_id:scoped.company.id,
            company_name:scoped.company.name, sector:scoped.company.sector,
            opportunities:{total:scoped.stats.opportunities},
            applications:{total:scoped.stats.applications},
            posts:{total:0}};
        } else {
          stats = await request('/backoffice/enterprise-dashboard/', 'GET', null, sessionToken);
          if (stats?.scope !== 'enterprise' ||
              stats.enterprise_id !== profile.enterprise_id ||
              !stats.opportunities || !stats.applications) {
            throw new Error('Statistiques de votre entreprise indisponibles.');
          }
        }
      } else {
        throw new Error('Ce compte ne possède pas d’espace professionnel administrable.');
      }
      if (generation !== version || token !== sessionToken) {
        throw new Error('La session a été fermée.');
      }
      current = { profile, stats };
      return current;
    } catch (error) {
      if (generation === version) disconnect();
      throw error;
    }
  }

  // Privileged roles never receive a browser credential before MFA is proven.
  async function startPrivilegedLogin(email, password) {
    disconnect();
    const version = generation;
    if (!email || !password) throw new Error('Adresse e-mail et mot de passe requis.');
    const data = await request('/users/web-login/', 'POST', { email, password });
    if (version !== generation) throw new Error('La session a été fermée.');
    if (!data?.mfa_required || !data.challenge || !['enroll', 'verify'].includes(data.mfa_action)) {
      throw new Error('Réponse de sécurité du serveur incompatible.');
    }
    return { challenge: data.challenge, action: data.mfa_action, email: data.email };
  }

  async function beginMfaSetup(challenge) {
    if (!challenge) throw new Error('Veuillez recommencer la connexion.');
    const data = await request('/users/web-mfa/setup/', 'POST', { challenge });
    if (!data?.secret || !data?.otpauth_uri) throw new Error('Configuration MFA incomplète.');
    return data;
  }

  async function finishMfa(challenge, code, roles) {
    if (!challenge || !code) throw new Error('Code MFA requis.');
    const version = generation;
    const data = await request('/users/web-mfa/verify/', 'POST', { challenge, code: String(code).trim() });
    if (version !== generation) throw new Error('La session a été fermée.');
    if (!data?.token || data.token_type !== 'WebToken') {
      throw new Error('Réponse de sécurité du serveur incompatible.');
    }
    if (!roles.includes(data.role)) {
      // The backend has issued a token, so revoke it immediately on a role mismatch.
      await request('/users/web-logout/', 'POST', {}, data.token, 'WebToken').catch(() => {});
      throw new Error('Ce compte appartient à un autre espace. Choisissez le bon profil.');
    }
    token = data.token;
    tokenKind = 'WebToken';
    try {
      let result;
      if (data.role === 'etablissement' || data.role === 'enterprise') {
        result = await refresh();
      } else {
        const profile = await request('/users/me/', 'GET', null, token);
        if (version !== generation) throw new Error('La session a été fermée.');
        if (!roles.includes(profile?.role)) throw new Error('Accès non autorisé à cet espace.');
        current = { profile };
        result = current;
      }
      return { ...result, recovery_codes: data.recovery_codes || [] };
    } catch (error) {
      if (version === generation) {
        const previous = token;
        disconnect();
        if (previous) await request('/users/web-logout/', 'POST', {}, previous, 'WebToken').catch(() => {});
      }
      throw error;
    }
  }

  // Resumes ONLY an already MFA-verified, unexpired browser device session.
  // The credential is returned in memory; it is never persisted by this client.
  async function restoreSession(role) {
    if (!['superAdmin','etablissement','enterprise'].includes(role)) return null;
    const version = generation;
    try {
      const data = await request('/users/web-resume/', 'POST', { role });
      if (generation !== version) return null;
      if (!data?.token || data.token_type !== 'WebToken' ||
          data.role !== role) {
        throw new Error('Réponse de reprise de session incompatible.');
      }
      token = data.token;
      tokenKind = 'WebToken';
      if (data.role === 'etablissement' || data.role === 'enterprise') return await refresh();
      const profile = await request('/users/me/', 'GET', null, token);
      if (generation !== version || token !== data.token ||
          profile?.role !== 'superAdmin') {
        throw new Error('Session administrative non autorisée.');
      }
      current = { profile };
      return current;
    } catch (_) {
      if (generation === version) disconnect();
      return null;
    }
  }

  // Alias retained for the E2 controller, now starts a challenge only.
  async function connect(email, password) {
    return startPrivilegedLogin(email, password);
  }

  async function logout() {
    const previous = token;
    const previousKind = tokenKind;
    disconnect();
    if (previous) await request(previousKind === 'WebToken' ? '/users/web-logout/' : '/users/logout/', 'POST', {}, previous, previousKind);
  }

  async function connectAccount(email, password, roles) {
    if (roles.some(role => ['etablissement', 'superAdmin', 'enterprise'].includes(role))) {
      throw new Error('Double authentification requise : utilisez la connexion sécurisée.');
    }
    disconnect();
    const version = generation;
    const data = await request('/users/login/', 'POST', { email, password });
    if (version !== generation) throw new Error('La session a été fermée.');
    if (!data?.token || !roles.includes(data.role)) {
      throw new Error('Ce compte appartient à un autre espace. Choisissez le bon profil.');
    }
    token = data.token;
    tokenKind = 'Token';
    try {
      const profile = await request('/users/me/', 'GET', null, token);
      if (version !== generation) throw new Error('La session a été fermée.');
      if (!roles.includes(profile.role)) throw new Error('Accès non autorisé à cet espace.');
      current = { profile };
      return current;
    } catch (error) {
      if (version === generation) disconnect();
      throw error;
    }
  }

  function enterpriseRequest(path, method = 'GET', payload = null) {
    if (!token || tokenKind !== 'WebToken' || current?.profile?.role !== 'enterprise' ||
        !current?.profile?.enterprise_id) {
      throw new Error('Session Entreprise vérifiée requise.');
    }
    if (!/^\/backoffice\/enterprise\/(offers|applications|publications)\/(?:[0-9]+\/)?$/.test(path)) {
      throw new Error('Action Entreprise non disponible.');
    }
    return request(path, method, payload, token, 'WebToken');
  }

  function privilegedRequest(path, method = 'GET', payload = null) {
    if (!token || tokenKind !== 'WebToken' || current?.profile?.role !== 'superAdmin') {
      throw new Error('Accès Superadmin sécurisé requis.');
    }
    return request(path, method, payload, token, 'WebToken');
  }
  // Commercial catalog requests only use the already MFA-verified device credential.
  function commercialRequest(path, method = 'GET', payload = null, admin = false) {
    const role = current?.profile?.role;
    if (!token || tokenKind !== 'WebToken' ||
        !['superAdmin', 'etablissement', 'enterprise'].includes(role) ||
        (admin && role !== 'superAdmin')) {
      throw new Error('Session professionnelle vérifiée requise.');
    }
    return request(path, method, payload, token, 'WebToken');
  }
  // E28: a single professional MFA session for the three account profiles.
  const professionalProfile = () => commercialRequest('/users/web-profile/');
  const professionalChangePassword = (current_password,new_password) => commercialRequest('/users/web-change-password/', 'POST', {current_password,new_password});
  const professionalProfileUpdate = async payload => {
    const profile = await commercialRequest('/users/web-profile/', 'PATCH', payload);
    if(current?.profile && profile){
      current.profile = {...current.profile, ...profile};
    }
    return profile;
  };
  const subscriptionCatalog = () => commercialRequest('/subscriptions/catalog/');
  const subscriptionMine = () => commercialRequest('/subscriptions/my/');
  const subscriptionSeats = () => commercialRequest('/subscriptions/institution/seats/');
  const subscriptionSetSeat = payload => commercialRequest('/subscriptions/institution/seats/', 'PATCH', payload);
  const adminUserDirectory = params => {
    const query=new URLSearchParams();
    for(const key of ['search','role','status','page','page_size']){
      if(params?.[key]!==undefined&&params[key]!==null&&String(params[key])!=='')
        query.set(key,String(params[key]));
    }
    return commercialRequest('/backoffice/user-directory/?'+query.toString(),'GET',null,true);
  };
  const adminUserSecurity = id => commercialRequest('/backoffice/user-directory/'+Number(id)+'/security/', 'GET', null, true);
  const financeRegister = params => {
    const query=new URLSearchParams();
    for(const key of ['status','search','page'])if(params?.[key]!==undefined && params[key]!==null)query.set(key,String(params[key]));
    return commercialRequest('/backoffice/finance/register/?'+query.toString(),'GET',null,true);
  };
  // E38: Invoice emission is admin-only; PDF download is tenant scoped server-side.
  const invoiceIssuer = () => commercialRequest('/backoffice/finance/issuer/', 'GET', null, true);
  const invoiceSaveIssuer = payload => commercialRequest('/backoffice/finance/issuer/', 'PUT', payload, true);
  const invoiceHistory = params => {
    const query=new URLSearchParams();
    for(const name of ['search','page'])
      if(params?.[name]!==undefined && params?.[name]!==null)query.set(name,String(params[name]));
    return commercialRequest('/backoffice/finance/invoices/?'+query.toString(), 'GET', null, true);
  };
  const invoiceIssue = payload => commercialRequest('/backoffice/finance/invoices/issue/','POST',payload,true);
  const myInvoices = params => {
    const query=new URLSearchParams();
    if(params?.page)query.set('page',String(params.page));
    return commercialRequest('/subscriptions/invoices/my/?'+query.toString());
  };
  const downloadInvoicePdf = async (id, number='', admin=true) => {
    if(!Number.isSafeInteger(Number(id))||Number(id)<1)throw new Error('Facture invalide.');
    const role=current?.profile?.role;
    if(!token||tokenKind!=='WebToken'||!['superAdmin','etablissement','enterprise'].includes(role)
      ||(admin&&role!=='superAdmin')||(!admin&&role==='superAdmin'))
      throw new Error('Session professionnelle vérifiée requise.');
    const path=admin?'/backoffice/finance/invoices/':'/subscriptions/invoices/';
    const controller=new AbortController();
    const timeout=setTimeout(()=>controller.abort(),18000);
    try{
      const response=await fetch(baseUrl()+path+Number(id)+'/pdf/', {
        method:'GET',
        headers:{'Authorization':'WebToken '+token,'Accept':'application/pdf'},
        cache:'no-store',credentials:'omit',signal:controller.signal,
      });
      if(!response.ok||!response.headers.get('Content-Type')?.includes('application/pdf')){
        const json=await response.json().catch(()=>null);
        throw new Error(json?.message||'Le PDF de cette facture est indisponible.');
      }
      const blob=await response.blob();
      if(blob.size<100||blob.type!=='application/pdf')throw new Error('PDF invalide.');
      const url=URL.createObjectURL(blob);
      const link=document.createElement('a');
      link.href=url;
      link.download=(String(number||'facture-'+id).replace(/[^A-Za-z0-9_-]/g,'')||'facture')+'.pdf';
      link.style.display='none';
      document.body.appendChild(link);link.click();link.remove();
      setTimeout(()=>URL.revokeObjectURL(url),1500);
      return true;
    }catch(error){
      if(error?.name==='AbortError')throw new Error('Téléchargement trop long. Réessayez.');
      throw error;
    }finally{clearTimeout(timeout);}
  };
  const adminUserSecurityAction = (id, action, reason) => commercialRequest('/backoffice/user-directory/'+Number(id)+'/security/', 'POST', {action, reason}, true);
  const enterprisePartnerDirectory = params => {
    const query = new URLSearchParams();
    for (const key of ['search','status','billing','page','page_size']) {
      if (params?.[key]!==undefined && params[key]!==null && String(params[key])!=='')
        query.set(key,String(params[key]));
    }
    return commercialRequest('/backoffice/enterprises/?'+query.toString(),'GET',null,true);
  };
  const institutionsDirectory = params => {
    const query=new URLSearchParams();
    for(const key of ['search','status','billing','page','page_size']){
      if(params?.[key]!==undefined&&params[key]!==null&&String(params[key])!=='')query.set(key,String(params[key]));
    }
    return commercialRequest('/backoffice/institutions/?'+query.toString(),'GET',null,true);
  };
  const pricingAdminOffers = () => commercialRequest('/subscriptions/admin/offers/', 'GET', null, true);
  const pricingAdminOrganisations = () => commercialRequest('/subscriptions/admin/organisations/', 'GET', null, true);
  const pricingAdminAssignments = () => commercialRequest('/subscriptions/admin/assignments/', 'GET', null, true);
  const pricingCreateOffer = payload => commercialRequest('/subscriptions/admin/offers/', 'POST', payload, true);
  const pricingUpdateOffer = (id, payload) => commercialRequest('/subscriptions/admin/offers/'+Number(id)+'/', 'PATCH', payload, true);
  const pricingSetPrice = payload => commercialRequest('/subscriptions/admin/prices/', 'POST', payload, true);
  const pricingRetirePrice = id => commercialRequest('/subscriptions/admin/prices/'+Number(id)+'/', 'PATCH', {is_active:false}, true);
  const pricingAssign = payload => commercialRequest('/subscriptions/admin/assignments/', 'POST', payload, true);
  const pricingUpdateAssignment = (id, payload) => commercialRequest('/subscriptions/admin/assignments/'+Number(id)+'/', 'PATCH', payload, true);
  const pricingAddCapacity = (id, payload) => commercialRequest('/subscriptions/admin/assignments/'+Number(id)+'/topups/', 'POST', payload, true);
  // E26: requests are user initiated, then independently reviewed by Superadmin.
  const subscriptionCheckoutConfig = () => commercialRequest('/subscriptions/checkout/config/');
  const subscriptionCheckoutOrders = () => commercialRequest('/subscriptions/checkout/orders/');
  const subscriptionCheckoutStart = price_option_id => commercialRequest('/subscriptions/checkout/start/', 'POST', {price_option_id});
  const subscriptionCheckoutVerify = transaction_id => commercialRequest('/subscriptions/checkout/'+encodeURIComponent(transaction_id)+'/verify/', 'POST', {});
  const subscriptionRequestsMine = () => commercialRequest('/subscriptions/requests/my/');
  const subscriptionCreateRequest = payload => commercialRequest('/subscriptions/requests/my/', 'POST', payload);
  const pricingAdminRequests = () => commercialRequest('/subscriptions/admin/requests/', 'GET', null, true);
  const pricingReviewRequest = (id, payload) => commercialRequest('/subscriptions/admin/requests/'+Number(id)+'/', 'PATCH', payload, true);
  // E54: enterprise invitations reuse the MFA-verified web session only.
  // Authorization and tenant isolation are enforced by Django.
  const enterpriseOwnerInvitations = () => privilegedRequest('/users/admin/enterprise-invitations/');
  const enterpriseInviteOwner = ({email, company_name, sector}) =>
    privilegedRequest('/users/admin/enterprise-invitations/', 'POST', {email, company_name, sector});
  const enterpriseMembership = () => commercialRequest('/users/enterprise/dashboard/');
  const enterpriseRecruiterInvitations = () => commercialRequest('/users/enterprise/invitations/');
  const enterpriseInviteRecruiter = (email) =>
    commercialRequest('/users/enterprise/invitations/', 'POST', {email});
  const enterpriseRecruiters = () => commercialRequest('/users/enterprise/recruiters/');
  // E57: real read-only global content directory, scoped to MFA Superadmin WebToken.
  // E58: only MFA Superadmin can review or confirm import batches.
  // E62: platform posture is aggregated; detailed device sessions belong to
  // the currently authenticated Superadmin, never to other accounts.
  const adminSecurityOverview = params => {
    const days=Number(params?.days??30);
    if(![7,30,90].includes(days))throw new Error('Période de sécurité invalide.');
    return privilegedRequest('/backoffice/security-v2/?days='+days);
  };
  const adminSecurityRevokeOwnSession = (id,payload) => {
    const key=Number(id);
    if(!Number.isSafeInteger(key)||key<1)throw new Error('Session invalide.');
    if(payload?.confirmation!=='REVOQUER')throw new Error('Confirmation obligatoire.');
    return privilegedRequest('/backoffice/security-v2/my-sessions/'+key+'/revoke/','POST',{confirmation:'REVOQUER'});
  };
  // E61: read-only audit register, authenticated via current Superadmin MFA.
  const adminAuditDirectory = params => {
    const query=new URLSearchParams();
    for(const key of ['days','category','action','search','page','page_size']){
      if(params?.[key]!==undefined&&params[key]!==null&&String(params[key])!=='')
        query.set(key,String(params[key]));
    }
    return privilegedRequest('/backoffice/audit-v2/?'+query.toString());
  };
  // E60: genuine aggregate stats for the verified Superadmin session only.
  const adminGlobalStatistics = params => {
    const days=Number(params?.days??180);
    if(![30,90,180,365].includes(days))throw new Error('Période de statistiques invalide.');
    return privilegedRequest('/backoffice/statistics-v2/?days='+days);
  };
  // E59: verified MFA Superadmin only, no access from the mobile feed.
  const adminModerationDirectory = params => {
    const query = new URLSearchParams();
    for(const key of ['status','reason','target','search','page','page_size']){
      if(params?.[key]!==undefined&&params[key]!==null&&String(params[key])!=='')
        query.set(key,String(params[key]));
    }
    return privilegedRequest('/backoffice/moderation-v2/?'+query.toString());
  };
  const adminModerationDecision = (id,payload) => {
    const value=Number(id);
    if(!Number.isSafeInteger(value)||value<1)throw new Error('Signalement invalide.');
    if(!payload||!['dismiss','hide_post'].includes(payload.decision))
      throw new Error('Décision de modération invalide.');
    return privilegedRequest('/backoffice/moderation-v2/'+value+'/decision/','POST',payload);
  };
  const adminImportHistory = params => {
    const query=new URLSearchParams();
    for(const key of ['page','type','institution_search']){
      if(params?.[key]!==undefined&&params[key]!==null&&String(params[key])!=='')
        query.set(key,String(params[key]));
    }
    return privilegedRequest('/backoffice/imports-v2/?'+query.toString());
  };
  const adminImportPreview = payload =>
    privilegedRequest('/backoffice/imports-v2/preview/','POST',payload);
  const adminImportExecute = payload =>
    privilegedRequest('/backoffice/imports-v2/execute/','POST',payload);
  const adminContentDirectory = params => {
    const query=new URLSearchParams();
    for(const key of ['type','state','search','page','page_size']){
      if(params?.[key]!==undefined&&params[key]!==null&&String(params[key])!=='')
        query.set(key,String(params[key]));
    }
    return privilegedRequest('/backoffice/content-directory/?'+query.toString());
  };
  const enterpriseReadOffers = () => commercialRequest('/users/enterprise/offers/');
  const enterpriseReadOfferApplications = id => {
    if (!Number.isSafeInteger(Number(id)) || Number(id) < 1) throw new Error('Offre invalide.');
    return commercialRequest('/users/enterprise/offers/'+Number(id)+'/applications/');
  };
  const enterpriseRevokeInvitation = id => {
    if (!Number.isSafeInteger(Number(id)) || Number(id) < 1) throw new Error('Invitation invalide.');
    return commercialRequest('/users/enterprise/invitations/'+Number(id)+'/revoke/', 'POST', {});
  };
  const enterpriseRevokeRecruiter = id => {
    if (!Number.isSafeInteger(Number(id)) || Number(id) < 1) throw new Error('Recruteur invalide.');
    return commercialRequest('/users/enterprise/recruiters/'+Number(id)+'/revoke/', 'POST', {});
  };
  // Public endpoints never require or leak a professional session.
  const enterprisePreviewInvitation = invitation =>
    request('/users/enterprise/invitations/preview/', 'POST', {invitation});
  const enterpriseAcceptInvitation = (invitation, password, first_name, last_name) =>
    request('/users/enterprise/invitations/accept/', 'POST',
      {invitation, password, first_name, last_name});
  const listInvitations = () => privilegedRequest('/users/admin/invitations/');
  const sendInvitation = (email, institution_id) => privilegedRequest('/users/admin/invitations/', 'POST', { email, institution_id });
  const revokeInvitation = (id) => {
    if (!Number.isSafeInteger(Number(id)) || Number(id) <= 0) throw new Error('Invitation inconnue.');
    return privilegedRequest('/users/admin/invitations/' + Number(id) + '/revoke/', 'POST', {});
  };
  const previewInvitation = invitation => request('/users/invitations/preview/', 'POST', { invitation });
  const acceptInvitation = (invitation, password, first_name, last_name) =>
    request('/users/invitations/accept/', 'POST', { invitation, password, first_name, last_name });

  window.GConnectEstablishmentApi = Object.freeze({
    connect,
    connectAccount,
    startPrivilegedLogin,
    beginMfaSetup,
    finishMfa,
    restoreSession,
    professionalProfile,
    professionalProfileUpdate,
    professionalChangePassword,
    subscriptionCatalog,
    subscriptionMine,
    subscriptionSeats,
    subscriptionSetSeat,
    enterpriseRequest,
    adminUserDirectory,
    adminUserSecurity,
    adminUserSecurityAction,
    financeRegister,
    invoiceIssuer, invoiceSaveIssuer, invoiceHistory, invoiceIssue,
    myInvoices, downloadInvoicePdf,
    enterprisePartnerDirectory,
    institutionsDirectory,
    pricingAdminOffers,
    pricingAdminOrganisations,
    pricingAdminAssignments,
    pricingCreateOffer,
    pricingUpdateOffer,
    pricingSetPrice,
    pricingRetirePrice,
    pricingAssign,
    pricingUpdateAssignment,
    pricingAddCapacity,
    subscriptionCheckoutConfig,
    subscriptionCheckoutOrders,
    subscriptionCheckoutStart,
    subscriptionCheckoutVerify,
    subscriptionRequestsMine,
    subscriptionCreateRequest,
    pricingAdminRequests,
    pricingReviewRequest,
    enterpriseOwnerInvitations, enterpriseInviteOwner,
    enterpriseMembership, enterpriseRecruiterInvitations, enterpriseInviteRecruiter,
    enterpriseRecruiters, enterpriseRevokeInvitation, enterpriseRevokeRecruiter,
    adminContentDirectory,
    adminModerationDirectory, adminModerationDecision,
    adminGlobalStatistics,
    adminAuditDirectory,
    adminSecurityOverview, adminSecurityRevokeOwnSession,
    adminImportHistory, adminImportPreview, adminImportExecute,
    enterpriseReadOffers, enterpriseReadOfferApplications,
    enterprisePreviewInvitation, enterpriseAcceptInvitation,
    listInvitations,
    sendInvitation,
    revokeInvitation,
    previewInvitation,
    acceptInvitation,
    logout,
    publicRequest: (path, payload) => {
      const allowed = ['/users/forgot-password/', '/users/reset-password/', '/users/verify-otp/', '/users/otp/resend/', '/users/register/student/check-code/', '/users/register/student/', '/users/register/alumni/'];
      if (!allowed.includes(path)) throw new Error('Action non disponible.');
      return request(path, 'POST', payload);
    },
    refresh,
    disconnect,
    isConnected: () => Boolean(token && current),
    getCurrent: () => current ? { profile: current.profile, stats: current.stats } : null,
  });
})();

