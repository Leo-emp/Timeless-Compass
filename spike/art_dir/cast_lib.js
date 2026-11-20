// Timeless Compass 2D cast library (spike): outline helpers, shared head, faces, hair/headgear.
// Copied out of cast_sheet.html so every sheet draws characters the same way.
// ---------- shared style constants ----------
const OUT = '#2a1c13';   // the one outline colour (dark warm brown, never pure black)
const SW  = 7;           // outline thickness in figure units
let uid = 0;             // counter so every clipPath gets a unique id

// shape with outline: any SVG tag + attributes, filled, stroked with the house outline
function sh(tag, attrs, fill){
  const a = Object.entries(attrs).map(([k,v])=>`${k}="${v}"`).join(' ');
  return `<${tag} ${a} fill="${fill}" stroke="${OUT}" stroke-width="${SW}" stroke-linejoin="round" stroke-linecap="round"/>`;
}
// plain line in outline colour (for folds, lacing, brows)
function ln(d, w=5, col=OUT){ return `<path d="${d}" fill="none" stroke="${col}" stroke-width="${w}" stroke-linecap="round" stroke-linejoin="round"/>`; }

// a "rubber" limb: a thick outline stroke with a thinner colour stroke on top = tube with outline
function limb(d, w, col){
  return `<path d="${d}" fill="none" stroke="${OUT}" stroke-width="${w+SW*2}" stroke-linecap="round" stroke-linejoin="round"/>`+
         `<path d="${d}" fill="none" stroke="${col}" stroke-width="${w}" stroke-linecap="round" stroke-linejoin="round"/>`;
}
// hand = small circle; drawn AFTER a held prop so the fist really wraps it
function hand(x,y,skin){ return sh('circle',{cx:x,cy:y,r:15},skin) + ln(`M${x-8} ${y-3} Q${x} ${y+4} ${x+8} ${y-3}`,3.5); }

// soft shade: fills the right side of a shape (light comes from upper-left)
// shapeSvg = the shape markup used as the clip; we lay a darker ellipse over its right part
function shade(clipInner, cx, cy, rx, ry, col='rgba(80,35,15,.16)'){
  const id = 'c'+(uid++);
  return `<clipPath id="${id}">${clipInner}</clipPath>`+
         `<ellipse cx="${cx}" cy="${cy}" rx="${rx}" ry="${ry}" fill="${col}" clip-path="url(#${id})"/>`;
}

// ---------- the head (shared by every character) ----------
// Head centre (0,-300), radius ~60. `ex` = expression name. `age` adds wrinkles.
function head(skin, ex='neutral', opt={}){
  let s = '';
  // ears first so the head outline sits over them
  s += sh('ellipse',{cx:-58,cy:-296,rx:11,ry:15},skin) + sh('ellipse',{cx:58,cy:-296,rx:11,ry:15},skin);
  s += sh('ellipse',{cx:0,cy:-300,rx:60,ry:63},skin);
  s += shade('<ellipse cx="0" cy="-300" rx="57" ry="60"/>', 52, -296, 42, 70);   // shade on the right cheek
  s += `<ellipse cx="-30" cy="-280" rx="11" ry="6" fill="rgba(230,110,90,.22)"/><ellipse cx="30" cy="-280" rx="11" ry="6" fill="rgba(230,110,90,.22)"/>`; // faint cheeks
  s += face(ex, opt);
  if (window.BLINK) s += `<ellipse cx="-21" cy="-300" rx="11" ry="14" fill="${skin}"/><ellipse cx="21" cy="-300" rx="11" ry="14" fill="${skin}"/>`+ln('M-30 -299 Q-21 -293 -12 -299',4.5)+ln('M12 -299 Q21 -293 30 -299',4.5);  // blink lids
  if (opt.age) s += ln('M-40 -322 Q-30 -326 -20 -322',2.5) + ln('M20 -322 Q30 -326 40 -322',2.5) + ln('M-46 -284 Q-42 -276 -44 -268',2.5) + ln('M46 -284 Q42 -276 44 -268',2.5);
  if (opt.beard) s += sh('path',{d:'M-50 -282 Q-48 -232 0 -226 Q48 -232 50 -282 Q40 -258 0 -256 Q-40 -258 -50 -282 Z'}, opt.beard);
  return s;
}

// facial expression: eyes, brows, nose, mouth. Small solid eyes like the reference.
function face(ex, opt={}){
  let s='', eyeY=-300;
  const eye = (x, ry=9)=> `<ellipse cx="${x}" cy="${eyeY}" rx="6.5" ry="${ry}" fill="${OUT}"/><circle cx="${x-2}" cy="${eyeY-3}" r="2" fill="#fff"/>`;
  // nose: one small curve
  s += ln('M-3 -288 Q3 -284 -1 -279',3.5);
  switch(ex){
    case 'neutral':
      s += eye(-21)+eye(21);
      s += ln('M-31 -322 L-12 -321',6)+ln('M12 -321 L31 -322',6);
      s += ln('M-10 -264 Q0 -260 10 -264',4.5); break;
    case 'stern':      // determined / angry: inner brow ends pushed down
      s += eye(-21,8)+eye(21,8);
      s += ln('M-33 -331 L-11 -318',7)+ln('M11 -318 L33 -331',7);
      s += ln('M-13 -259 Q0 -266 13 -259',5); break;
    case 'worried':    // inner brow ends raised, wobbly mouth, sweat drop
      s += eye(-21)+eye(21);
      s += ln('M-32 -318 L-11 -330',6)+ln('M11 -330 L32 -318',6);
      s += ln('M-12 -262 Q-6 -267 0 -262 Q6 -257 12 -262',4.5);
      s += `<path d="M56 -342 Q64 -326 56 -320 Q48 -326 56 -342 Z" fill="#8fc6e8" stroke="${OUT}" stroke-width="3.5"/>`; break;
    case 'shocked':    // bigger eyes, high brows, open mouth
      s += `<ellipse cx="-21" cy="${eyeY}" rx="9" ry="12" fill="${OUT}"/><ellipse cx="21" cy="${eyeY}" rx="9" ry="12" fill="${OUT}"/><circle cx="-24" cy="-305" r="2.5" fill="#fff"/><circle cx="18" cy="-305" r="2.5" fill="#fff"/>`;
      s += ln('M-32 -334 Q-21 -340 -10 -334',6)+ln('M10 -334 Q21 -340 32 -334',6);
      s += sh('ellipse',{cx:0,cy:-260,rx:9,ry:12},'#7a2b22'); break;
    case 'sly':        // one brow up, half-closed eyes, smirk
      s += ln('M-29 -301 Q-21 -296 -13 -301',5)+ln('M13 -301 Q21 -296 29 -301',5);
      s += ln('M-31 -318 L-12 -317',6)+ln('M12 -326 Q22 -332 32 -324',6);
      s += ln('M-10 -264 Q4 -262 14 -270',4.5); break;
    case 'grief':      // brows up in the middle, eyes looking down, downturned mouth
      s += `<ellipse cx="-21" cy="-296" rx="6" ry="7" fill="${OUT}"/><ellipse cx="21" cy="-296" rx="6" ry="7" fill="${OUT}"/>`;
      s += ln('M-31 -316 L-12 -326',6)+ln('M12 -326 L31 -316',6);
      s += ln('M-11 -258 Q0 -266 11 -258',4.5);
      s += `<path d="M-24 -288 Q-21 -278 -24 -272" stroke="#8fc6e8" stroke-width="4" fill="none" stroke-linecap="round"/>`; break;
  }
  return s;
}

// ---------- hair & headgear ----------
const hair = {
  // Edo/Sengoku topknot: shaved crown, hair on the sides, small knot laid on top
  chonmage(){ return sh('path',{d:'M-60 -292 Q-64 -330 -46 -344 L-40 -318 Q-50 -306 -52 -284 Z'},'#22201f')+
                     sh('path',{d:'M60 -292 Q64 -330 46 -344 L40 -318 Q50 -306 52 -284 Z'},'#22201f')+
                     sh('rect',{x:-8,y:-388,width:16,height:34,rx:8},'#22201f')+ln('M-8 -362 L8 -362',3,'#c9b27a'); },
  // Sengoku kabuto: lacquered bowl, flared neck guard, turned-back flaps, gold crescent crest
  kabuto(){ return sh('path',{d:'M-70 -318 Q-92 -290 -96 -262 L-62 -276 L-60 -318 Z'},'#7a1f1a')+
                   sh('path',{d:'M70 -318 Q92 -290 96 -262 L62 -276 L60 -318 Z'},'#7a1f1a')+
                   ln('M-66 -300 L-90 -286',3.5)+ln('M66 -300 L90 -286',3.5)+
                   sh('path',{d:'M-68 -316 Q-68 -380 0 -384 Q68 -380 68 -316 Z'},'#2b2a33')+
                   ln('M-40 -372 L-42 -318',3,'#55546a')+ln('M0 -384 L0 -318',3,'#55546a')+ln('M40 -372 L42 -318',3,'#55546a')+
                   sh('path',{d:'M-74 -318 Q0 -326 74 -318 L74 -306 Q0 -314 -74 -306 Z'},'#2b2a33')+
                   sh('path',{d:'M-30 -330 Q-62 -392 -40 -440 Q-46 -386 0 -350 Q46 -386 40 -440 Q62 -392 30 -330 Z'},'#e0b347'); },
  // Greek Corinthian helmet pushed up on the head (face visible), red horsehair crest
  corinthian(){ return sh('path',{d:'M-64 -404 Q-66 -488 0 -492 Q66 -488 64 -404 Q40 -436 0 -438 Q-40 -436 -64 -404 Z'},'#b23a2a')+ln('M-40 -440 Q-44 -470 -20 -480 M0 -440 L0 -488 M40 -440 Q44 -470 20 -480',2.5,'#7e2419')+
                       sh('path',{d:'M-62 -330 Q-66 -404 0 -408 Q66 -404 62 -330 L48 -326 L44 -350 L-44 -350 L-48 -326 Z'},'#c99a45')+
                       ln('M-44 -350 L44 -350',3,'#8a6427')+
                       shade('<path d="M-62 -330 Q-66 -404 0 -408 Q66 -404 62 -330 Z"/>', 50, -370, 40, 60, 'rgba(90,50,10,.2)')+
                       sh('rect',{x:-8,y:-428,width:16,height:24,rx:3},'#8a6427'); },
  // Roman senator: short greying hair combed forward
  roman(){ return sh('path',{d:'M-60 -300 Q-66 -366 0 -368 Q66 -366 60 -300 Q56 -334 30 -340 Q0 -332 -30 -340 Q-56 -334 -60 -300 Z'},'#9c958d')+
                  ln('M-30 -340 L-26 -330',3)+ln('M-6 -336 L-4 -326',3)+ln('M18 -338 L16 -328',3); },
  // Egyptian New Kingdom wig: black bob with straight fringe
  wig(){ return sh('path',{d:'M-70 -240 Q-80 -380 0 -376 Q80 -380 70 -240 L48 -240 L50 -300 Q46 -330 30 -334 L-30 -334 Q-46 -330 -50 -300 L-48 -240 Z'},'#1c1a22')+
                ln('M-60 -300 L-60 -250',2.5,'#3a3846')+ln('M60 -300 L60 -250',2.5,'#3a3846'); },
  // 1950s fedora
  fedora(){ return sh('path',{d:'M-58 -300 Q-62 -340 -40 -346 L40 -346 Q62 -340 58 -300 Z'},'#4b3a2a')+
                   sh('ellipse',{cx:0,cy:-346,rx:88,ry:16},'#3b2e22')+
                   sh('path',{d:'M-50 -348 Q-50 -404 0 -398 Q50 -404 50 -348 Z'},'#3b2e22')+
                   ln('M0 -398 L0 -386',4)+sh('rect',{x:-50,y:-364,width:100,height:14,rx:3},'#1f1814'); },
};

