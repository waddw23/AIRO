#!/usr/bin/env bash
set -euo pipefail

SRC="demo-output/mobile-keynote-white-iphone-style-fast60.mp4"
OUT1="demo-output/promo-social-9x16.mp4"
OUT2="demo-output/promo-social-1x1.mp4"

ffmpeg -y -ss 0 -t 15 -i "$SRC" \
  -vf "
    scale=1080:-2:flags=lanczos,
    crop=1080:1920:(iw-1080)/2:(ih-1920)/2,
    fps=30,
    drawbox=x=0:y=0:w=iw:h=220:color=white@0.70:t=fill,
    drawbox=x=0:y=1700:w=iw:h=220:color=white@0.76:t=fill,
    drawtext=text='AIRON Enterprise Commerce AI':x=54:y=56:fontsize=54:fontcolor=#0D1B35:alpha='if(lt(t,0.6),t/0.6,1)',
    drawtext=text='发布会级智能电商平台':x=56:y=124:fontsize=44:fontcolor=#2454A6:alpha='if(lt(t,0.9),t/0.9,1)',
    drawtext=text='AI策略中枢  实时经营看板  智能客服质检':x=56:y=1790:fontsize=40:fontcolor=#123468:alpha='if(lt(t,1.1),t/1.1,1)',
    drawtext=text='1. 结构化AI回答  2. 渠道增长洞察  3. 企业级自动化':x=62:y=420:fontsize=42:fontcolor=white:enable='between(t,2,5.2)',
    drawtext=text='4. GMV/ROI/FCR实时追踪  5. 指标波动秒级反馈':x=62:y=420:fontsize=42:fontcolor=white:enable='between(t,5.2,8.4)',
    drawtext=text='6. SKU机会地图  7. 客服SLA与质检联动':x=62:y=420:fontsize=42:fontcolor=white:enable='between(t,8.4,11.6)',
    drawtext=text='8. 面向社交电商与全渠道增长的AI底座':x=62:y=420:fontsize=42:fontcolor=white:enable='between(t,11.6,14)',
    drawtext=text='立即接入  AIRON':x=(w-text_w)/2:y=1640:fontsize=62:fontcolor=#FFFFFF:enable='between(t,13.7,15)',
    fade=t=in:st=0:d=0.6:color=white,
    fade=t=out:st=14.4:d=0.6:color=white
  " \
  -an -c:v libx264 -preset medium -crf 19 -pix_fmt yuv420p -movflags +faststart "$OUT1"

ffmpeg -y -ss 0 -t 15 -i "$OUT1" \
  -vf "
    scale=1080:1920:flags=lanczos,
    crop=1080:1080:0:420,
    fps=30,
    drawbox=x=0:y=0:w=iw:h=110:color=white@0.72:t=fill,
    drawbox=x=0:y=970:w=iw:h=110:color=white@0.72:t=fill,
    drawtext=text='AIRON Commerce AI':x=34:y=28:fontsize=50:fontcolor=#0D1B35,
    drawtext=text='发布会宣传版':x=36:y=994:fontsize=42:fontcolor=#1F4D9E
  " \
  -an -c:v libx264 -preset medium -crf 19 -pix_fmt yuv420p -movflags +faststart "$OUT2"

printf '%s\n%s\n' "$OUT1" "$OUT2"
