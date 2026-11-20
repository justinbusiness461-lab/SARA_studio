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
                    library:"platformLibraryPanel",profile:"platformProfilePanel"};
  function text(id,value) {const node=$(id);if(node)node.textContent=value;}
  function changeView(view) {
    currentView=view;
    root.classList.toggle("platform-view-studio",view==="studio"||view==="chat");
    for(const [key,id] of Object.entries(surfaces))$(id).hidden=key!==view;
    for(const button of $("platformNavigation").querySelectorAll("button")){
      const active=button.dataset.platformView===view;
      if(active)button.setAttribute("aria-current","page");else button.removeAttribute("aria-current");
    }
    if(view==="chat") $("studioPromptSurface")?.scrollIntoView({block:"start",behavior:"instant"});
    if(view==="explore") loadExplore().catch(error=>text("platformExploreStatus","ERROR · "+error.message));
    if(view==="library") loadLibrary().catch(error=>text("platformLibraryStatus","ERROR · "+error.message));
    if(view==="profile") loadProfile().catch(error=>text("platformProfileStatus","ERROR · "+error.message));
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

