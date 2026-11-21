/* PLATFORM-01/02: One account, lawful catalog, existing Studio and Chat.
 * Presentation only; session, rights, publication and media truth are server-owned.
 */
(() => {
  if (!window.__SARA_PLATFORM_MODE__) return;
  const $ = id => document.getElementById(id);
  const root = document.body;
  let currentArtist = null;
  let pendingChatApproval = null;
  let currentView = "home";
  let currentExploreTab="discover", activeRoomId=null;

  function clearChatApproval() {
    pendingChatApproval=null;
    const button=$("platformChatApprove");
    if(button){button.hidden=true;button.disabled=false;}
  }
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
    if(view==="explore") showExploreTab(currentExploreTab);
    if(view==="library") loadLibrary().catch(error=>text("platformLibraryStatus","ERROR · "+error.message));
    if(view==="profile") {
      loadProfile().catch(error=>text("platformProfileStatus","ERROR · "+error.message));
      refreshWave2().catch(error=>text("platformPlaylistStatus","ERROR · "+error.message));
    }
    if(view==="home") text("platformHomeStatus","READY · Open your library or continue in Studio");
  }
  function showSignedOut(message="READY · Sign in or create your account"){
    clearChatApproval();
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
  function showExploreTab(tab){
    currentExploreTab=tab;
    $("platformSearch").hidden=tab!=="discover";
    $("platformDoSearch").hidden=tab!=="discover";
    $("platformExploreSongs").hidden=tab!=="discover";
    $("platformExploreStatus").hidden=tab!=="discover";
    $("platformRoomView").hidden=tab!=="rooms";
    $("platformCreatorView").hidden=tab!=="creators";
    for(const [id,name] of [["platformExploreTabDiscover","discover"],["platformExploreTabRooms","rooms"],["platformExploreTabCreators","creators"]]){
      if(tab===name)$(id).setAttribute("aria-current","true");else $(id).removeAttribute("aria-current");
    }
    if(tab==="discover")loadExplore().catch(e=>text("platformExploreStatus","ERROR · "+e.message));
    if(tab==="rooms")loadRoomList().catch(e=>text("platformRoomStatus","ERROR · "+e.message));
  }
  async function findCreator(){
    const handle=$("platformCreatorHandle").value.trim().replace(/^@/,"");
    try{const result=await request('/api/artists/'+encodeURIComponent(handle));
      text('platformCreatorResult',"@"+result.profile.handle+" · "+result.profile.displayName+" · "+result.songs.length+" public songs");
    }catch(e){text('platformCreatorResult',"NOT FOUND · "+e.message);}
  }
  async function loadRoomList(){
    const query=$("platformRoomSearch").value.trim();
    const result=await request('/api/explore/rooms?q='+encodeURIComponent(query));
    const list=$("platformRoomList");list.replaceChildren();
    for(const room of result.rooms){
      const button=document.createElement('button');button.type='button';
      button.textContent=room.name+' · '+room.category+' · '+room.visibility+' · '+room.memberCount+' members';
      button.addEventListener('click',()=>openRoom(room.roomId,room.name));list.append(button);
    }
    text('platformRoomStatus','READY · '+result.rooms.length+' available room(s)');
  }
  async function openRoom(id,name='Room'){
    activeRoomId=id;
    $("platformRoomDetail").hidden=false;$("platformRoomSidebar").hidden=false;
    text('platformRoomHeading',name);
    await refreshRoom();
  }
  async function refreshRoom(){
    if(!activeRoomId)return;
    try{
      const data=await request('/api/explore/rooms/'+activeRoomId+'/messages');
      const messages=$("platformRoomMessages"),people=$("platformRoomPeople"),listening=$("platformRoomListening");
      messages.replaceChildren();people.replaceChildren();listening.replaceChildren();
      for(const m of data.messages){
        const line=document.createElement('p');line.textContent='@'+m.handle+': '+m.body;messages.append(line);
      }
      for(const p of data.participants){
        const line=document.createElement('p');line.textContent='@'+p.handle+' · '+p.role+(p.observedRecently?' · recently active':'');people.append(line);
      }
      const player=$("platformAudio");
      for(const song of data.listeningStation){
        const item=document.createElement('button');item.type='button';item.textContent='Play '+song.title+' · @'+song.artist.handle;
        item.addEventListener('click',async()=>{
          try{
            // Revalidate on every play; published pointer never authorizes historical CAS.
            const proof=await request('/api/songs/'+encodeURIComponent(song.publicationId));
            player.src=proof.song.audioUrl;text('platformNowPlaying',proof.song.title);
            await player.play();
          }catch(e){player.pause();player.removeAttribute('src');text('platformRoomStatus','PLAYBACK DENIED · '+e.message);}
        });listening.append(item);
      }
      await loadRoomProposals();
      text('platformRoomStatus','READY · '+data.messages.length+' room messages · '+data.participants.length+' members');
    }catch(e){
      $("platformRoomMessages").replaceChildren();$("platformRoomPeople").replaceChildren();$("platformRoomListening").replaceChildren();$("platformRoomProposals").replaceChildren();
      text('platformRoomStatus','JOIN REQUIRED OR DENIED · '+e.message);
    }
  }
  async function loadRoomProposals(){
    if(!activeRoomId)return;
    const roomId=activeRoomId,holder=$("platformRoomProposals");
    const result=await request('/api/explore/rooms/'+roomId+'/proposals');
    if(roomId!==activeRoomId)return; // A late response cannot replace another room's inbox.
    holder.replaceChildren();
    for(const item of result.proposals){
      const card=document.createElement('article');card.className='platform-project-card';
      const brief=document.createElement('p');
      brief.textContent='@'+item.authorHandle+' · '+item.state+' · '+item.instruction;
      const open=document.createElement('button');open.type='button';
      open.textContent='Open source project in Studio (review only)';
      open.disabled=item.state!=='AWAITING_OWNER_REVIEW';
      open.addEventListener('click',()=>{
        if(!currentArtist||!window.confirm('Open the Studio project for separate review? This does NOT approve or commit the proposal.'))return;
        const input=$("projectId"),button=$("btnOpenProject");
        if(!input||!button){text('platformRoomStatus','ERROR · Studio owner UI unavailable');return;}
        input.value=item.projectId;changeView('studio');button.click();
      });
      card.append(brief,open);holder.append(card);
    }
  }
  async function createRoom(){
    try{
      const name=$("platformRoomName").value.trim();
      const room=await request('/api/explore/rooms','POST',{name,category:$("platformRoomCategory").value,
        visibility:$("platformRoomVisibility").value,maxOccupancy:16});
      await loadRoomList();await openRoom(room.roomId,name);
      $("platformRoomName").value='';
    }catch(e){text('platformRoomStatus','ERROR · '+e.message);}
  }
  async function roomAction(action,payload={}){
    if(!activeRoomId)return text('platformRoomStatus','ERROR · Select a room');
    try{
      const outcome=await request('/api/explore/rooms/'+activeRoomId+'/'+action,'POST',payload);
      if(action==='messages')$("platformRoomComposer").value='';
      text('platformRoomStatus',outcome.state||outcome.status||'READY');
      await refreshRoom();
    }catch(e){text('platformRoomStatus','NOT COMMITTED · '+e.message);}
  }
  async function roomProposal(){
    if(!activeRoomId)return;
    try{
      const result=await request('/api/explore/rooms/'+activeRoomId+'/propose-collaboration','POST',{
        workspaceId:$("platformRoomWorkspace").value.trim(),
        projectId:$("platformRoomProject").value.trim(),
        baseRevisionId:$("platformRoomRevision").value.trim(),
        instruction:$("platformRoomProposal").value.trim()});
      text('platformRoomStatus',result.state+' · Not committed · '+result.proposalId);
    }catch(e){text('platformRoomStatus','PROPOSAL DENIED · '+e.message);}
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
    clearChatApproval();
    text("platformChatStatus","LOADING · Checking authenticated command");
    text("platformChatResult","");
    if(!instruction){text("platformChatStatus","ERROR · Enter a command");return;}
    try{
      const context=sourceBoundChatContext();
      const result=await request("/api/platform/chat","POST",{instruction,context});
      if(!currentArtist || currentArtist.principalId!==artist)return;
      text("platformChatStatus",result.state+" · "+result.action);
      text("platformChatResult",result.message||JSON.stringify(result.result,null,2));
      if(result.state==="APPROVAL_REQUIRED"&&result.approval_challenge_id){
        const project=context.projectId,revision=context.revisionId;
        if(!project||!revision||result.projectId!==project||result.sourceRevisionId!==revision)
          throw new Error("Approval requires an exact currently selected source revision");
        pendingChatApproval={
          challengeId:result.approval_challenge_id,
          action:result.action,
          digest:result.operation_digest,
          principalId:artist,projectId:project,revisionId:revision,
          artifactId:context.artifactId||null,
          expiresAtUnix:result.expiresAtUnix
        };
        $("platformChatApprove").hidden=false;
        text("platformChatResult",JSON.stringify({
          action:result.action,sourceRevisionId:revision,
          operationDigest:result.operation_digest,
          expectedCurrentRevisionId:revision,
          message:result.message,expiresAtUnix:result.expiresAtUnix,
          warning:"Not committed. A separate approval is required; owner rights/locks may still deny."
        },null,2));
      }
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
  async function approvePlatformChat(){
    const selection=pendingChatApproval;
    if(!selection)return;
    clearChatApproval(); // Never allow a second submission while outcome is ambiguous.
    const artist=currentArtist?.principalId;
    if(!artist || artist!==selection.principalId){
      text("platformChatStatus","DENIED · Account changed");return;
    }
    if(!selection.expiresAtUnix||Date.now()/1000>=selection.expiresAtUnix){
      text("platformChatStatus","DENIED · Approval expired; request a new proposal");return;
    }
    let current;
    try{current=sourceBoundChatContext();}
    catch(error){text("platformChatStatus","DENIED · "+error.message);return;}
    if(current.projectId!==selection.projectId||current.revisionId!==selection.revisionId||
       (selection.artifactId&&current.artifactId!==selection.artifactId)){
      text("platformChatStatus","DENIED · Project, revision or audio selection changed");return;
    }
    const warning=selection.action==="PUBLISH"?"Publicly reveal this source revision after rights verification?":
      "Approve "+selection.action+" on this exact source revision? The server will recheck rights, locks and revision authority.";
    if(!window.confirm(warning)){
      text("platformChatStatus","DECLINED · No operation performed");return;
    }
    text("platformChatStatus","EXECUTING · Server validating single-use approval…");
    try{
      const result=await request("/api/m045/chat/approve","POST",{
        approval_challenge_id:selection.challengeId,
        expected_current_revision_id:selection.revisionId});
      if(currentArtist?.principalId!==artist)return;
      const digest=result.operationResult?.artifactId||null;
      text("platformChatStatus","EXECUTED · "+result.action+" · Read back authoritative state");
      text("platformChatResult",JSON.stringify({
         action:result.action,revisionCommitted:result.revisionCommitted,
         operationDigest:result.operationDigest,sourceRevisionId:result.sourceRevisionId,
         outputRevisionId:result.operationResult?.revisionId||null,
         outputArtifactId:digest,
         rightsStatus:result.operationResult?.rightsStatus||null,
         audioStatus:result.operationResult?.audioStatus||null,
         telemetry:result.operationResult?.telemetry||null,
         publicationId:result.operationResult?.publicationId||null,
         preservationTier:result.operationResult?.preservationTier||"UNVERIFIED"
      },null,2));
    }catch(error){
      text("platformChatStatus","NOT VERIFIED · "+error.message+" · Check revision history before reissuing");
    }
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
  // Revision identity comes only from the existing Studio proof/selection.
  // The server independently authenticates every media read and write.
  function r14Source(){
    const c=sourceBoundChatContext();
    if(!c.projectId||!c.revisionId||!c.artifactId)
      throw new Error('Open and verify exact Studio revision audio first');
    return {projectId:c.projectId,revisionId:c.revisionId,artifactId:c.artifactId};
  }
  let activePreviewGrant=null,markerFrameCount=0;
  function renderWaveformMarkers(result){
    const list=$('platformWaveformMarkers'),canvas=$('platformWaveformMarkersCanvas');
    list.replaceChildren();
    const max=Math.max(1,Number(result.totalSamples)||1),ctx=canvas.getContext('2d');
    markerFrameCount=max;
    if(ctx){
      const w=canvas.width,h=canvas.height;
      ctx.clearRect(0,0,w,h);ctx.strokeStyle='#3d97bd';ctx.lineWidth=2;
      ctx.beginPath();ctx.moveTo(5,h/2);ctx.lineTo(w-5,h/2);ctx.stroke();
      for(const marker of result.comments||[]){
        const x=5+(w-10)*Math.min(1,Number(marker.samplePosition)/max);
        ctx.strokeStyle='#87f0ec';ctx.lineWidth=3;ctx.beginPath();
        ctx.moveTo(x,8);ctx.lineTo(x,h-8);ctx.stroke();
      }
    }
    for(const marker of result.comments||[]){
      const item=document.createElement('li');
      item.textContent='sample '+marker.samplePosition+' · '+marker.barBeatLabel+' · '+marker.body;
      list.append(item);
    }
    text('platformFeedbackStatus','READY · '+(result.comments||[]).length+
      ' marker(s) · exact revision '+result.revisionId.slice(0,12));
  }
  async function refreshR14Feedback(){
    try{
      const src=r14Source();
      const q=new URLSearchParams(src);
      const result=await request('/api/feedback/comments?'+q.toString());
      if(JSON.stringify(src)!==JSON.stringify(r14Source()))return;
      renderWaveformMarkers(result);
    }catch(e){text('platformFeedbackStatus','NOT VERIFIED · '+e.message);}
  }
  async function addR14Feedback(){
    try{
      const src=r14Source(),position=Number($('platformFeedbackPosition').value);
      if(!Number.isSafeInteger(position)||position<0)throw new Error('Invalid sample position');
      const payload={...src,samplePosition:position,
        barBeatLabel:$('platformFeedbackBeat').value.trim(),
        body:$('platformFeedbackBody').value.trim()};
      await request('/api/feedback/comments','POST',payload);
      $('platformFeedbackBody').value='';
      await refreshR14Feedback();
    }catch(e){text('platformFeedbackStatus','NOT COMMITTED · '+e.message);}
  }
  async function createR14Preview(){
    try{
      const grant=await request('/api/previews/grants','POST',
        {...r14Source(),expiresInSeconds:1800});
      activePreviewGrant=grant.grantId;
      $('platformPreviewShareUrl').value=new URL(grant.audioUrl,location.origin).href;
      $('platformPreviewRevoke').disabled=false;
      text('platformPreviewStatus','PRIVATE LINK READY · expires in 30 minutes · revocable');
    }catch(e){text('platformPreviewStatus','NOT SHARED · '+e.message);}
  }
  async function revokeR14Preview(){
    if(!activePreviewGrant)return;
    try{
      await request('/api/previews/'+encodeURIComponent(activePreviewGrant)+'/revoke','POST',{});
      activePreviewGrant=null;
      $('platformPreviewRevoke').disabled=true;
      $('platformPreviewShareUrl').value='';
      text('platformPreviewStatus','REVOKED · further audio and metadata reads denied');
    }catch(e){text('platformPreviewStatus','REVOKE NOT VERIFIED · '+e.message);}
  }
  async function prepareR14Release(){
    let payload;
    try{
      payload={...r14Source(),title:$('platformReleaseTitle').value.trim(),
        artistHandle:currentArtist?.handle||'',
        genre:$('platformReleaseGenre').value.trim(),
        coverArtSha256:$('platformReleaseCover').value.trim(),
        rightsStatus:$('platformReleaseRights').value};
    }catch(e){text('platformReleaseStatus','NOT PREPARED · '+e.message);return;}
    if(!window.confirm('Approve exact revision and release metadata for PREPARATION only? No DSP publication or Content ID is authorized.')){
      text('platformReleaseStatus','DECLINED · no release operation');return;
    }
    text('platformReleaseStatus','CHECKING · preparing exact revision package');
    try{
      const approval=await request('/api/release/approve','POST',
        {...payload,confirmRelease:true});
      // Single-use token stays in memory. No blind retry after an ambiguous effect.
      const result=await request('/api/release/prepare','POST',
        {...payload,approvalToken:approval.approvalToken});
      text('platformReleaseStatus',result.publicationState+' · '+result.packageId+
        ' · not published · Content ID NOT entitled');
    }catch(e){
      text('platformReleaseStatus','NOT VERIFIED · '+e.message+
        ' · inspect package authority before attempting again');
    }
  }
  $('platformFeedbackLoad').addEventListener('click',refreshR14Feedback);
  $('platformFeedbackAdd').addEventListener('click',addR14Feedback);
  $('platformPreviewCreate').addEventListener('click',createR14Preview);
  $('platformPreviewRevoke').addEventListener('click',revokeR14Preview);
  $('platformReleasePrepare').addEventListener('click',prepareR14Release);
  $('platformWaveformMarkersCanvas').addEventListener('pointerup',event=>{
    if(!markerFrameCount)return;
    const bounds=event.currentTarget.getBoundingClientRect();
    $('platformFeedbackPosition').value=String(Math.max(0,Math.min(markerFrameCount-1,
      Math.floor((event.clientX-bounds.left)/bounds.width*markerFrameCount))));
  });
  for(const el of $("platformNavigation").querySelectorAll("button"))
    el.addEventListener("click",()=>changeView(el.dataset.platformView));
  $("platformStartCreating").addEventListener("click",()=>changeView("studio"));
  for(const [id,tab] of [["platformExploreTabDiscover","discover"],["platformExploreTabRooms","rooms"],["platformExploreTabCreators","creators"]])
    $(id).addEventListener('click',()=>showExploreTab(tab));
  $("platformFindCreator").addEventListener('click',findCreator);
  $("platformCreateRoom").addEventListener('click',createRoom);
  $("platformRoomSearchButton").addEventListener('click',()=>loadRoomList().catch(e=>text('platformRoomStatus','ERROR · '+e.message)));
  $("platformRoomRefresh").addEventListener('click',refreshRoom);
  $("platformRoomReviewRefresh").addEventListener('click',()=>loadRoomProposals().catch(e=>text('platformRoomStatus','REVIEW DENIED · '+e.message)));
  $("platformRoomJoin").addEventListener('click',()=>roomAction('join'));
  $("platformRoomLeave").addEventListener('click',()=>roomAction('leave'));
  $("platformRoomSend").addEventListener('click',()=>roomAction('messages',{body:$("platformRoomComposer").value}));
  $("platformRoomPin").addEventListener('click',()=>roomAction('pin-track',{publicationId:$("platformRoomPinId").value.trim()}));
  for(const action of ['invite','kick','block'])
    $("platformRoom"+action[0].toUpperCase()+action.slice(1)).addEventListener('click',()=>roomAction(action,{handle:$("platformRoomInviteHandle").value.trim()}));
  $("platformRoomPropose").addEventListener('click',roomProposal);
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
  $("platformChatApprove").addEventListener("click",approvePlatformChat);
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

