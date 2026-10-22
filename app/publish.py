#!/usr/bin/env python3
"""Official API publishing. Instagram gets a temporary public GitHub Release asset."""
from __future__ import annotations
import argparse, json, os, sys, time
from datetime import datetime, timezone
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from pathlib import Path

API_TIMEOUT=90

def request_json(url, method='GET', data=None, headers=None, timeout=API_TIMEOUT):
    h={'User-Agent':'AI-Broskyee-AutoFactory/1.0',**(headers or {})}
    payload=None if data is None else json.dumps(data).encode('utf-8')
    if payload is not None: h.setdefault('Content-Type','application/json')
    req=Request(url,data=payload,headers=h,method=method)
    try:
        with urlopen(req,timeout=timeout) as r:
            raw=r.read()
            if not raw:return {}
            return json.loads(raw.decode('utf-8'))
    except HTTPError as e:
        msg=e.read(2500).decode('utf-8','replace')
        raise RuntimeError(f'HTTP {e.code} from {url.split("?")[0]}: {msg}') from e

def youtube_upload(video_path: Path, plan: dict) -> dict:
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request as GoogleRequest
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
    client_id=os.environ['YT_CLIENT_ID']; client_secret=os.environ['YT_CLIENT_SECRET']; refresh=os.environ['YT_REFRESH_TOKEN']
    creds=Credentials(None,refresh_token=refresh,token_uri='https://oauth2.googleapis.com/token',client_id=client_id,client_secret=client_secret,scopes=['https://www.googleapis.com/auth/youtube.upload'])
    creds.refresh(GoogleRequest())
    yt=build('youtube','v3',credentials=creds,cache_discovery=False)
    desc=str(plan.get('description','')).strip()+"\n\nOriginal AI-Broskyee animation."
    for src in plan.get('source_candidates',[])[:3]:
        if src.get('url'): desc+=f"\nTopic inspiration: {src.get('title','Source')} — {src['url']}"
    desc+='\n#Shorts'
    body={'snippet':{'title':str(plan.get('title','AI-Broskyee Original Short'))[:100], 'description':desc[:4800], 'tags':plan.get('tags',[])[:8]+['Shorts','AI-Broskyee'], 'categoryId':os.environ.get('YT_CATEGORY_ID','28'), 'defaultLanguage':'en'},'status':{'privacyStatus':os.environ.get('YT_PRIVACY_STATUS','public'),'selfDeclaredMadeForKids':False}}
    req=yt.videos().insert(part='snippet,status',body=body,media_body=MediaFileUpload(str(video_path),mimetype='video/mp4',resumable=True,chunksize=8*1024*1024))
    response=None
    while response is None:
        _,response=req.next_chunk()
    vid=response['id']
    # Verify the actual state; some unverified API clients can be restricted to private uploads.
    state=yt.videos().list(part='status',id=vid).execute().get('items',[{}])[0].get('status',{})
    return {'video_id':vid,'url':f'https://www.youtube.com/shorts/{vid}','requested_privacy':body['status']['privacyStatus'],'actual_privacy':state.get('privacyStatus','unknown')}

def github_release_asset(video_path: Path, title: str) -> tuple[dict,str]:
    token=os.environ['GITHUB_TOKEN']; repo=os.environ['GITHUB_REPOSITORY']
    headers={'Authorization':f'Bearer {token}','Accept':'application/vnd.github+json','X-GitHub-Api-Version':'2022-11-28'}
    tag='autofactory-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    release=request_json(f'https://api.github.com/repos/{repo}/releases','POST',{'tag_name':tag,'name':'Temporary AI-Broskyee Reel asset','body':'Temporary video asset for immediate Instagram API publishing; automatically deleted after successful publish.','draft':False,'prerelease':True},headers)
    upload_url=release['upload_url'].split('{',1)[0]+ '?'+urlencode({'name':video_path.name})
    with video_path.open('rb') as f: data=f.read()
    # Release video is meant to be short; avoid unexpectedly huge public assets.
    if len(data)>180*1024*1024: raise RuntimeError('Video exceeds the safe temporary Instagram asset limit (180 MB).')
    req=Request(upload_url,data=data,headers={**headers,'Content-Type':'video/mp4'},method='POST')
    try:
        with urlopen(req,timeout=180) as r: asset=json.loads(r.read().decode('utf-8'))
    except HTTPError as e: raise RuntimeError(f'GitHub release asset upload failed: {e.code} {e.read(2000).decode("utf-8","replace")}') from e
    return release,asset['browser_download_url']

def instagram_publish(video_url: str, plan: dict) -> dict:
    user=os.environ['IG_USER_ID']; token=os.environ['IG_ACCESS_TOKEN']; version=os.environ.get('IG_GRAPH_VERSION','v25.0').strip()
    base=f'https://graph.instagram.com/{version}/{user}'
    q=urlencode({'media_type':'REELS','video_url':video_url,'caption':(str(plan.get('title','AI-Broskyee Short'))+'\n\n'+str(plan.get('description',''))+'\n\n'+' '.join('#'+str(t).replace(' ','') for t in plan.get('tags',[])[:6])+' #Reels #AIanimation')[:2200],'share_to_feed':'true','access_token':token})
    container=request_json(base+'/media?'+q,'POST')
    cid=container.get('id')
    if not cid: raise RuntimeError(f'Instagram did not return a media container id: {container}')
    state={}
    for _ in range(36):
        state=request_json(f'{base}/{cid}?'+urlencode({'fields':'status_code,status','access_token':token}),'GET')
        code=state.get('status_code')
        if code=='FINISHED': break
        if code in ('ERROR','EXPIRED'): raise RuntimeError(f'Instagram media processing failed: {state}')
        time.sleep(5)
    if state.get('status_code')!='FINISHED': raise RuntimeError(f'Instagram processing timed out: {state}')
    published=request_json(base+'/media_publish?'+urlencode({'creation_id':cid,'access_token':token}),'POST')
    media_id=published.get('id')
    if not media_id: raise RuntimeError(f'Instagram publish did not return an id: {published}')
    return {'media_id':media_id,'container_id':cid}

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--video',required=True); ap.add_argument('--plan',required=True); ap.add_argument('--out',default='output/publish-result.json'); a=ap.parse_args()
    video=Path(a.video); plan=json.loads(Path(a.plan).read_text(encoding='utf-8'))
    required=('YT_CLIENT_ID','YT_CLIENT_SECRET','YT_REFRESH_TOKEN','IG_USER_ID','IG_ACCESS_TOKEN','GITHUB_TOKEN','GITHUB_REPOSITORY')
    missing=[k for k in required if not os.environ.get(k,'').strip()]
    if missing: raise SystemExit('Missing credentials; nothing published: '+', '.join(missing))
    result={'published':False,'platforms':{}}
    release=None
    try:
        release,public_url=github_release_asset(video,plan.get('title','AI-Broskyee Short'))
        # Publish to Instagram first, then upload to YouTube. Cross-platform publishing is not atomic.
        result['platforms']['instagram']=instagram_publish(public_url,plan)
        result['platforms']['youtube']=youtube_upload(video,plan)
        actual_privacy=result['platforms']['youtube'].get('actual_privacy','unknown')
        result['published_to_both']=actual_privacy=='public'
        result['published']=result['published_to_both']
        if actual_privacy!='public':
            result['warning']='Instagram was published, but YouTube reports actual privacy '+str(actual_privacy)+'. The YouTube API client may require its official audit before public posting.'
        result['temporary_asset_deleted']=False
        try:
            gh_headers={'Authorization':f'Bearer {os.environ["GITHUB_TOKEN"]}','Accept':'application/vnd.github+json','X-GitHub-Api-Version':'2022-11-28'}
            request_json(f'https://api.github.com/repos/{os.environ["GITHUB_REPOSITORY"]}/releases/{release["id"]}','DELETE',headers=gh_headers)
            # Delete the git tag too; deleting a GitHub Release alone leaves its tag behind.
            tag=release.get('tag_name','')
            if tag:
                request_json(f'https://api.github.com/repos/{os.environ["GITHUB_REPOSITORY"]}/git/refs/tags/{tag}','DELETE',headers=gh_headers)
            result['temporary_asset_deleted']=True
        except Exception as e:
            result['cleanup_warning']=str(e)
    except Exception as exc:
        result['error']=str(exc)
        if release: result['temporary_release_url']=release.get('html_url')
        raise
    finally:
        out=Path(a.out); out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result,indent=2))
if __name__=='__main__': main()
