/* PLATFORM-01/02: One account, lawful catalog, existing Studio and Chat.
 * Presentation only; session, rights, publication and media truth are server-owned.
 */
(() => {
  if (!window.__SARA_PLATFORM_MODE__) return;
  const $ = id => document.getElementById(id);
  const root = document.body;
  let currentArtist = null;
  let currentView = "home";
  const surfaces = {home:"platformHomePanel",explore:"platformExplorePanel",
                    library:"platformLibraryPanel",profile:"platformProfilePanel",
                    chat:"platformChatPanel"};
  function text(id,value) {const node=$(id);if(node)node.textContent=value;}
  function changeView(view) {
    currentView=view;
    root.classList.toggle("platform-view-studio",view==="studio");
    for(const [key,id] of Object.entries(surfaces))$(id).hidden=key!==view;
    for(const button of $("platformNavigation").querySelectorAll("button")){
      const active=button.dataset.platformView===view;
      if(active)button.setAttribute("aria-current","page");else button.removeAttribute("aria-current");
    }
    if(view==="chat") $("platformChatInstruction")?.focus();
    if(view==="explore") loadExplore().catch(error=>text("platformExploreStatus","ERROR · "+error.message));
    if(view==="library") loadLibrary().catch(error=>text("platformLibraryStatus","ERROR · "+error.message));
    if(view==="profile") {
      loadProfile().catch(error=>text("platformProfileStatus","ERROR · "+error.message));
      refreshWave2().catch(error=>text("platformPlaylistStatus","ERROR · "+error.message));
    }
    if(view==="home") text("platformHomeStatus","READY · Open your library or continue in Studio");
  }
  function showSignedOut(message="READY · Sign in or create your account"){
    currentArtist=null;
    root.classList.remove("platform-signed-in","platform-view-studio");
    root.classList.add("platform-signed-out");
    $("platformShell").hidden=true;
    $("platformAuth").hidden=false;
    $("platformPublishPanel").hidden=true;
    text("platformAuthStatus",message);
  }
  function showSignedIn(me) {
    currentArtist=me;
    root.classList.remove("platform-signed-out");
    root.classList.add("platform-signed-in");
    $("platformAuth").hidden=true;
    $("platformShell").hidden=false;
    $("platformPublishPanel").hidden=false;
    text("platformActiveArtist","@"+me.handle);
    changeView("home");
  }
  async function request(path,method="GET",data=null){
    const opts={method,credentials:"same-origin",headers:{"X-Studio-Capability":window.__STUDIO_CAPABILITY__||""}};
    if(data!==null){opts.headers["Content-Type"]="application/json";opts.body=JSON.stringify(data);}
    let response;
    try{response=await fetch(path,opts);}
    catch(error){throw new Error("Network unavailable");}
    const result=await response.json().catch(()=>({}));
    if(!response.ok)throw new Error(result.error||result.status||"HTTP "+response.status);
    return result;
  }
  async function authenticate(kind){
    const handle=$("platformHandle").value.trim();
    const password=$("platformPassword").value;
    text("platformAuthStatus","LOADING · Checking secure account");
    for(const el of ["platformSignIn","platformSignUp"])$(el).disabled=true;
    try{
      if(kind==="signup")await request("/api/auth/signup","POST",
       {handle,password,displayName:$("platformDisplayName").value.trim()});
      await request("/api/auth/login","POST",{handle,password});
      const result=await request("/api/me");
      $("platformPassword").value="";
      showSignedIn(result.account);
    }catch(error){text("platformAuthStatus","ERROR · "+error.message);}
    finally{for(const el of ["platformSignIn","platformSignUp"])$(el).disabled=false;}
  }
  function addSong(container,song){
    const card=document.createElement("article");card.className="platform-song-card";
    const strong=document.createElement("strong");strong.textContent=song.title;
    const artist=document.createElement("span");artist.textContent="@"+song.artist.handle;
    const play=document.createElement("button");play.type="button";play.textContent="Play released song";
    play.addEventListener("click",()=>{
      $("platformAudio").src=song.audioUrl;
      text("platformNowPlaying",song.title);
      $("platformAudio").play().catch(()=>text("platformExploreStatus","ERROR · Playback denied or unsupported"));
    });
    card.append(strong,artist,play);container.append(card);
  }
  async function loadExplore(search=false) {
    text("platformExploreStatus","LOADING · Searching authorized public music");
    $("platformExploreSongs").replaceChildren();
    const query=$("platformSearch").value.trim();
    const result=await request(search?"/api/search?q="+encodeURIComponent(query):"/api/explore");
    if(!result.songs?.length){text("platformExploreStatus","EMPTY · No published songs match yet");return;}
    for(const song of result.songs)addSong($("platformExploreSongs"),song);
    text("platformExploreStatus","READY · "+result.songs.length+" published song(s)");
  }
  async function loadLibrary() {
    text("platformLibraryStatus","LOADING · Reading authorized project library");
    $("platformLibraryProjects").replaceChildren();
    const result=await request("/api/me/library");
    if(!result.projects?.length){text("platformLibraryStatus","EMPTY · Create your first saved project");return;}
    for(const project of result.projects){
      const article=document.createElement("article");article.className="platform-project-card";
      const title=document.createElement("strong");title.textContent=project.title;
      const open=document.createElement("button");open.type="button";open.textContent="Open saved revision in Studio";
      open.addEventListener("click",()=>{
        $("projectId").value=project.projectId;
        changeView("studio");
        $("btnOpenProject").click();
      });
      article.append(title,open);$("platformLibraryProjects").append(article);
    }
    text("platformLibraryStatus","READY · "+result.projects.length+" project(s)");
  }
  async function loadProfile(){
    text("platformProfileStatus","LOADING · Reading artist profile");
    const result=await request("/api/me/profile");
    $("platformProfileHandle").value=result.profile.handle;
    $("platformProfileName").value=result.profile.displayName;
    $("platformBio").value=result.profile.bio;
    text("platformProfileStatus","READY · Profile loaded");
  }
  async function saveProfile(){
    text("platformProfileStatus","LOADING · Saving profile");
    try{
      const result=await request("/api/me/profile","PUT",{
        handle:$("platformProfileHandle").value,displayName:$("platformProfileName").value,bio:$("platformBio").value});
      currentArtist=result.profile;
      text("platformActiveArtist","@"+result.profile.handle);
      text("platformProfileStatus","READY · Profile saved");
    }catch(error){text("platformProfileStatus","ERROR · "+error.message);}
  }
  async function listPlaylists(){
    const result=await request("/api/playlists");
    const panel=$("platformMyPlaylists");panel.replaceChildren();
    for(const item of result.playlists){
      const card=document.createElement("div");card.className="platform-project-card";
      card.textContent=item.title+" · "+item.visibility;panel.append(card);
    }
    text("platformPlaylistStatus","READY · "+result.playlists.length+" playlist(s)");
  }
  async function createPlaylist(){
    text("platformPlaylistStatus","LOADING · Creating private playlist");
    try {
      await request("/api/playlists","POST",{title:$("platformPlaylistTitle").value,visibility:"private"});
      await listPlaylists();
      $("platformPlaylistTitle").value="";
    } catch(e) {text("platformPlaylistStatus","ERROR · "+e.message);}
  }
  async function createAlbum(){
    text("platformAlbumStatus","LOADING · Saving private album");
    try {
      const result=await request("/api/albums","POST",{title:$("platformAlbumTitle").value});
      text("platformAlbumStatus","READY · Private album draft "+result.albumId+" · No tracks published");
      $("platformAlbumTitle").value="";
    }catch(e){text("platformAlbumStatus","ERROR · "+e.message);}
  }
  async function listWorkspaces(){
    const result=await request("/api/workspaces");
    const panel=$("platformMyWorkspaces"),selector=$("platformWorkspaceSelect");
    panel.replaceChildren();selector.replaceChildren();
    for(const item of result.workspaces){
      const card=document.createElement("div");card.className="platform-project-card";
      card.textContent=item.name+" · "+item.role;panel.append(card);
      if(item.role==="owner"){
        const opt=document.createElement("option");opt.value=item.workspaceId;opt.textContent=item.name;
        selector.append(opt);
      }
    }
    text("platformWorkspaceStatus","READY · "+result.workspaces.length+" workspace(s)");
  }
  async function createWorkspace(){
    text("platformWorkspaceStatus","LOADING · Creating workspace");
    try{
      await request("/api/workspaces","POST",{name:$("platformWorkspaceName").value});
      await listWorkspaces();$("platformWorkspaceName").value="";
    }catch(e){text("platformWorkspaceStatus","ERROR · "+e.message);}
  }
  async function workspaceMember(action){
    text("platformWorkspaceStatus","LOADING · Checking owner permissions");
    try{
      const wid=$("platformWorkspaceSelect").value;
      if(!wid)throw new Error("Create or select a workspace");
      const data={handle:$("platformWorkspaceInviteHandle").value.trim()};
      if(action==="invite")data.role=$("platformWorkspaceInviteRole").value;
      const result=await request("/api/workspaces/"+wid+"/"+action,"POST",data);
      text("platformWorkspaceStatus","READY · "+(action==="invite"?"Invitation grant saved":"Member revoked"));
    }catch(e){text("platformWorkspaceStatus","ERROR · "+e.message);}
  }
  async function showCreditBalance(){
    text("platformCreditsStatus","LOADING · Checking authoritative ledger");
    try{
      const result=await request("/api/credits/balance");
      text("platformCreditsStatus","READY · "+result.available+" available · "+result.reserved+" reserved · "+result.spent+" settled");
    }catch(e){text("platformCreditsStatus","ERROR · "+e.message);}
  }
  async function socialAction(action){
    text("platformSocialStatus","LOADING · Checking artist permissions");
    try{
      const result=await request("/api/social/action","POST",{action,handle:$("platformSocialHandle").value.trim()});
      text("platformSocialStatus","READY · "+action+" recorded");
    }catch(e){text("platformSocialStatus","ERROR · "+e.message);}
  }
  async function showNotifications(){
    text("platformNotificationsStatus","LOADING · Checking notifications");
    try{
      const result=await request("/api/notifications"),panel=$("platformNotifications");
      panel.replaceChildren();
      for(const item of result.notifications){
        const row=document.createElement("p");row.textContent=item.kind+" · "+item.actor;panel.append(row);
      }
      text("platformNotificationsStatus","READY · "+result.notifications.length+" notification(s)");
    }catch(e){text("platformNotificationsStatus","ERROR · "+e.message);}
  }
  async function refreshWave2(){
    await Promise.all([listPlaylists(),listWorkspaces(),showCreditBalance(),showNotifications()]);
  }
  function sourceBoundChatContext(){
    // Presentation adapter only: exact Studio-authoritative project selection.
    // No browser-supplied revision, rights status or CAS digest is trusted by server.
    const context={};
    const ref=typeof durableProjectRef!=="undefined"?durableProjectRef:null;
    if(ref?.projectId&&ref?.revisionId){
      context.projectId=ref.projectId;
      context.revisionId=ref.revisionId;
      const proof=window.__M044_PLAYBACK_PROOF__;
      if(proof?.projectId===ref.projectId && proof?.revisionId===ref.revisionId
        && proof?.artifactId)context.artifactId=proof.artifactId;
    }
    const selected=$("m045TargetTrack")?.value;
    if(selected&&context.projectId)context.selectedTrackId=selected;
    const rawBars=$("platformChatBars")?.value.trim();
    if(rawBars){
      if(!/^\d{1,4}(?:\s*,\s*\d{1,4})*$/.test(rawBars))throw new Error("Select bars as comma-separated numbers");
      context.selectedBars=rawBars.split(",").map(x=>Number(x.trim()));
    }
    return context;
  }
  async function executePlatformChat(){
    const instruction=$("platformChatInstruction").value.trim();
    const artist=currentArtist?.principalId;
    text("platformChatStatus","LOADING · Checking authenticated command");
    text("platformChatResult","");
    if(!instruction){text("platformChatStatus","ERROR · Enter a command");return;}
    try{
      const context=sourceBoundChatContext();
      const result=await request("/api/platform/chat","POST",{instruction,context});
      if(!currentArtist || currentArtist.principalId!==artist)return;
      text("platformChatStatus",result.state+" · "+result.action);
      text("platformChatResult",result.message||JSON.stringify(result.result,null,2));
      if(result.state==="STUDIO_ACTION_READY"&&result.action==="GENERATE"){
        const prompt=$("prompt"),button=$("btnCompile");
        if(!prompt||!button||!result.prompt)throw new Error("Existing Studio Generate control unavailable");
        const prior=prompt.value.trim();
        // The shipped example prompt is not an artist-authored draft.
        // Preserve genuinely edited drafts unless the artist confirms replacement.
        const isBundledExample=prior===prompt.dataset.studioExamplePrompt;
        const artistEditedDraft=prior&&!isBundledExample;
        if(artistEditedDraft&&prior!==result.prompt&&!window.confirm("Replace the unsaved Studio prompt with this Chat request?")){
          text("platformChatStatus","NOT SUBMITTED · Existing draft preserved");
          return;
        }
        prompt.value=result.prompt;
        changeView("studio");
        button.click(); // exact existing Studio/ScoreCore owner, not Chat-owned music
        text("platformChatStatus","STUDIO SUBMITTED · Check the resulting revision and audio Proof");
      }
      if(result.action==="CREATE_PRIVATE_PLAYLIST")await listPlaylists();
      if(result.action==="SEARCH_QUEUE_PRIVATE_PLAYLIST"&&result.result?.queue?.length){
        const first=result.result.songs[0];
        $("platformAudio").src=first.audioUrl;
        text("platformNowPlaying",first.title+" · queued via Chat");
        await listPlaylists();
      }
    }catch(e){text("platformChatStatus","ERROR · "+e.message);}
  }
  async function publishCurrent(){
    text("platformPublishStatus","LOADING · Checking selected revision and rights");
    const ref=typeof durableProjectRef!=="undefined"?durableProjectRef:null;
    const proof=typeof verifiedPlayback!=="undefined"?verifiedPlayback:null;
    if(!ref||!proof||proof.projectId!==ref.projectId||proof.revisionId!==ref.revisionId
      ||typeof proof.artifactId!=="string"){
      text("platformPublishStatus","ERROR · Verify current revision audio before publishing");
      return;
    }
    if(!window.confirm("Publish this exact selected music revision to Explore? This makes its accepted audio public.")){
      text("platformPublishStatus","NOT PUBLISHED · Artist declined");return;
    }
    try{
      const output=await request("/api/publications","POST",{projectId:ref.projectId,
        revisionId:ref.revisionId,artifactId:proof.artifactId,confirmPublic:true});
      text("platformPublishStatus","READY · Published ID "+output.publicationId);
    }catch(error){text("platformPublishStatus","NOT PUBLISHED · "+error.message);}
  }
  for(const el of $("platformNavigation").querySelectorAll("button"))
    el.addEventListener("click",()=>changeView(el.dataset.platformView));
  $("platformStartCreating").addEventListener("click",()=>changeView("studio"));
  $("platformDoSearch").addEventListener("click",()=>loadExplore(true).catch(e=>text("platformExploreStatus","ERROR · "+e.message)));
  $("platformSearch").addEventListener("keydown",e=>{if(e.key==="Enter")$("platformDoSearch").click();});
  $("platformSignIn").addEventListener("click",()=>authenticate("signin"));
  $("platformSignUp").addEventListener("click",()=>authenticate("signup"));
  $("platformSaveProfile").addEventListener("click",saveProfile);
  $("platformCreatePlaylist").addEventListener("click",createPlaylist);
  $("platformCreateAlbum").addEventListener("click",createAlbum);
  $("platformCreateWorkspace").addEventListener("click",createWorkspace);
  $("platformWorkspaceInvite").addEventListener("click",()=>workspaceMember("invite"));
  $("platformWorkspaceRevoke").addEventListener("click",()=>workspaceMember("revoke"));
  $("platformCreditsRefresh").addEventListener("click",showCreditBalance);
  $("platformFollow").addEventListener("click",()=>socialAction("follow"));
  $("platformBlock").addEventListener("click",()=>socialAction("block"));
  $("platformNotificationsRefresh").addEventListener("click",showNotifications);
  $("platformChatSend").addEventListener("click",executePlatformChat);
  $("platformPublishCurrent").addEventListener("click",publishCurrent);
  $("platformLogout").addEventListener("click",async()=>{
    try{await request("/api/auth/logout","POST",{});}catch(_){}
    showSignedOut("READY · Signed out");
    $("platformAudio").pause();$("platformAudio").removeAttribute("src");
    // Clear Studio's JS-only revision/playback state across account boundary.
    window.location.reload();
  });
  // The existing offline cache might contain an old local-only HTML bootstrap.
  // Platform pages and any server-injected capability must never be served offline.
  if("serviceWorker" in navigator)
    navigator.serviceWorker.getRegistrations()
      .then(regs=>Promise.all(regs.map(reg=>reg.unregister()))).catch(()=>{});
  showSignedOut("LOADING · Checking existing account session");
  request("/api/me").then(result=>showSignedIn(result.account))
    .catch(()=>showSignedOut());
})();

