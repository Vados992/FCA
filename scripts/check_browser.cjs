/* Optional UI acceptance test. Requires Node.js and playwright 1.62.1 with Chromium.
   FCEA_PYTHON selects the interpreter; FCEA_BROWSER_OUTPUT selects screenshots/report. */
'use strict';
const {chromium}=require('playwright');
const fs=require('node:fs');
const os=require('node:os');
const path=require('node:path');
const net=require('node:net');
const {spawn,spawnSync}=require('node:child_process');
const root=path.resolve(__dirname,'..');
const python=process.env.FCEA_PYTHON||'python';
const directory=fs.mkdtempSync(path.join(os.tmpdir(),'fcea-browser-'));
const output=path.resolve(process.env.FCEA_BROWSER_OUTPUT||path.join(root,'validation-output','browser'));
fs.mkdirSync(output,{recursive:true});
const delay=ms=>new Promise(resolve=>setTimeout(resolve,ms));
async function unusedPort(){const server=net.createServer();await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));const port=server.address().port;await new Promise(resolve=>server.close(resolve));return port;}
async function main(){
  const port=await unusedPort();
  const server=spawn(python,['-m','fcea','--data-dir',directory,'serve','--port',String(port)],{cwd:root,stdio:['ignore','ignore','pipe']});
  let errors='';server.stderr.on('data',data=>{errors+=data.toString();});
  let browser;
  try{
    const url='http://127.0.0.1:'+port;
    let ready=false;
    for(let i=0;i<100;i++){try{const r=await fetch(url+'/healthz');if(r.ok){ready=true;break;}}catch{}await delay(100);}
    if(!ready)throw new Error('Server did not start: '+errors);
    const tokens=JSON.parse(fs.readFileSync(path.join(directory,'credentials.local.json'),'utf8')).one_time_tokens;
    browser=await chromium.launch({headless:true,args:['--no-sandbox']});
    const context=await browser.newContext({viewport:{width:1440,height:1100},acceptDownloads:true});
    const page=await context.newPage();const pageErrors=[];
    page.on('pageerror',error=>pageErrors.push(error.message));
    await page.goto(url);
    async function login(token){await page.locator('#token').fill(token);await page.locator('#login-form button').click();await page.locator('#workspace').waitFor({state:'visible'});}
    await login(tokens.analyst);
    await page.locator('#example-select').selectOption('policy-rct');
    await page.locator('#load-example').click();
    await page.waitForFunction(()=>document.querySelector('#protocol-select').value==='policy_rct.protocol');
    await page.locator('#run-protocol').click();
    await page.waitForFunction(()=>document.querySelectorAll('#run-detail .gate').length===16);
    if(await page.locator('#run-detail .gate.fail').count())throw new Error('Unexpected failed gate in browser');
    await page.screenshot({path:path.join(output,'dashboard-desktop.png'),fullPage:true});
    const download=page.waitForEvent('download');
    await page.getByRole('button',{name:'Download proof packet'}).click();
    const packet=await download;const packetPath=path.join(output,'browser-proof.zip');await packet.saveAs(packetPath);
    const replay=spawnSync(python,['-m','fcea','proof','reproduce',packetPath],{cwd:root,encoding:'utf8',timeout:60000});
    if(replay.status!==0)throw new Error('Downloaded proof did not reproduce: '+replay.stderr+replay.stdout);
    await page.getByRole('button',{name:'Linked graphs',exact:true}).click();
    if(await page.locator('#graph-body tr').count()<1)throw new Error('Graph relationships missing');
    await page.getByRole('button',{name:'Domain adapters',exact:true}).click();
    if(await page.locator('#adapter-grid article').count()!==8)throw new Error('Adapter cards missing');
    await page.getByRole('button',{name:'Analysis runs',exact:true}).click();
    await page.setViewportSize({width:390,height:844});
    const overflow=await page.evaluate(()=>document.documentElement.scrollWidth>window.innerWidth);
    if(overflow)throw new Error('Mobile layout has horizontal overflow');
    await page.screenshot({path:path.join(output,'dashboard-mobile.png'),fullPage:true});
    await page.locator('#disconnect').click();
    await login(tokens.reviewer);
    await page.locator('.run-button').first().click();
    await page.getByLabel('Review rationale').fill('Synthetic UI acceptance review; no real-world scientific endorsement.');
    await page.getByRole('button',{name:'Submit review',exact:true}).click();
    await page.waitForFunction(()=>document.querySelector('#message').textContent.includes('Immutable review recorded'));
    if(!await page.locator('#run-protocol').isDisabled())throw new Error('Reviewer has analyst actions enabled');
    if(pageErrors.length)throw new Error('Browser errors: '+pageErrors.join('; '));
    const report={status:'PASS',browser:await browser.version(),playwright:require('playwright/package.json').version,
      checks:['bearer login','load synthetic example','freeze and run','16 gates','proof download and replay','graphs','8 adapter cards','390px mobile layout','reviewer disposition','role controls'],
      page_errors:pageErrors,proof_reproduction:JSON.parse(replay.stdout)};
    fs.writeFileSync(path.join(output,'browser-report.json'),JSON.stringify(report,null,2)+'\n');
    console.log(JSON.stringify(report,null,2));
  }finally{
    if(browser)await browser.close();
    server.kill('SIGTERM');await new Promise(resolve=>{if(server.exitCode!==null)resolve();else server.once('exit',resolve);});
    fs.rmSync(directory,{recursive:true,force:true});
  }
}
main().catch(error=>{console.error(error.message);process.exitCode=1;});
