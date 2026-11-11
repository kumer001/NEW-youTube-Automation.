import React from 'react';
import {
  AbsoluteFill,
  Audio,
  Easing,
  Sequence,
  interpolate,
  spring,
  staticFile,
  useCurrentFrame,
} from 'remotion';

export type Emoji = {char: string; x: number; y: number; size: number; anim: string};
export type Scene = {caption: string; emojis: Emoji[]; bg: [string, string]; audio: string; frames: number};
export type StoryProps = {durationInFrames: number; music: string; scenes: Scene[]};

const FONT =
  "'Noto Sans','Noto Sans Devanagari','Noto Sans Bengali','Noto Sans Tamil','Noto Sans Telugu','Noto Sans Arabic',sans-serif";
const EMOJI_FONT = "'Noto Color Emoji',sans-serif";
const clamp = {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'} as const;

const EmojiSprite: React.FC<{e: Emoji; i: number; f: number}> = ({e, i, f}) => {
  const pop = spring({frame: f - i * 7, fps: 30, config: {damping: 9, stiffness: 120}});
  let dx = 0;
  let dy = 0;
  let rot = 0;
  switch (e.anim) {
    case 'bounce':
      dy = -Math.abs(Math.sin((f + i * 5) / 8)) * 70;
      break;
    case 'float':
      dy = Math.sin((f + i * 9) / 18) * 35;
      dx = Math.sin((f + i * 4) / 27) * 18;
      break;
    case 'spin':
      rot = (f * 5) % 360;
      break;
    case 'shake':
      dx = Math.sin(f * 1.6) * 14;
      rot = Math.sin(f * 1.1) * 6;
      break;
    case 'slide':
      dx = interpolate(f - i * 7, [0, 22], [-700, 0], {...clamp, easing: Easing.out(Easing.back(1.5))});
      break;
    default:
      rot = Math.sin((f + i * 6) / 14) * 8;
  }
  return (
    <div
      style={{
        position: 'absolute',
        left: `${e.x}%`,
        top: `${e.y}%`,
        fontSize: e.size,
        lineHeight: 1,
        fontFamily: EMOJI_FONT,
        transform: `translate(-50%,-50%) translate(${dx}px,${dy}px) rotate(${rot}deg) scale(${pop})`,
        filter: 'drop-shadow(0 14px 0 rgba(0,0,0,0.22))',
      }}
    >
      {e.char}
    </div>
  );
};

const SceneView: React.FC<{s: Scene}> = ({s}) => {
  const f = useCurrentFrame();
  const fade = interpolate(f, [0, 6], [0, 1], clamp);
  const zoom = interpolate(f, [0, Math.max(2, s.frames)], [1, 1.07], clamp);
  const cap = spring({frame: f - 4, fps: 30, config: {damping: 10, stiffness: 140}});
  const long = s.caption.length > 28;
  return (
    <AbsoluteFill style={{opacity: fade, background: `linear-gradient(160deg, ${s.bg[0]}, ${s.bg[1]})`}}>
      <AbsoluteFill style={{transform: `scale(${zoom})`}}>
        {[0, 1, 2, 3, 4].map((k) => (
          <div
            key={k}
            style={{
              position: 'absolute',
              left: `${((k * 23 + f * 0.25) % 130) - 15}%`,
              top: `${8 + k * 13}%`,
              width: 260 + k * 40,
              height: 110 + k * 14,
              borderRadius: 999,
              background: 'rgba(255,255,255,0.22)',
            }}
          />
        ))}
        {s.emojis.map((e, i) => (
          <EmojiSprite key={i} e={e} i={i} f={f} />
        ))}
      </AbsoluteFill>
      <div
        style={{
          position: 'absolute',
          left: 60,
          right: 60,
          bottom: 200,
          textAlign: 'center',
          transform: `rotate(-2deg) scale(${cap})`,
        }}
      >
        <span
          style={{
            display: 'inline-block',
            background: '#fff',
            color: '#1b1b1b',
            border: '8px solid #1b1b1b',
            borderRadius: 40,
            padding: '28px 40px',
            fontFamily: FONT,
            fontWeight: 900,
            fontSize: long ? 62 : 78,
            lineHeight: 1.15,
            boxShadow: '0 14px 0 rgba(0,0,0,0.3)',
          }}
        >
          {s.caption}
        </span>
      </div>
    </AbsoluteFill>
  );
};

export const Story: React.FC<StoryProps> = ({scenes, music, durationInFrames}) => {
  const f = useCurrentFrame();
  let from = 0;
  const progress = interpolate(f, [0, durationInFrames], [0, 100], clamp);
  return (
    <AbsoluteFill style={{background: '#111'}}>
      {scenes.map((s, i) => {
        const start = from;
        from += s.frames;
        return (
          <Sequence key={i} from={start} durationInFrames={s.frames}>
            <SceneView s={s} />
            {s.audio ? (
              <Sequence from={5}>
                <Audio src={staticFile(s.audio)} />
              </Sequence>
            ) : null}
          </Sequence>
        );
      })}
      {music ? <Audio src={staticFile(music)} volume={0.12} loop /> : null}
      <div style={{position: 'absolute', top: 0, left: 0, height: 14, width: `${progress}%`, background: '#fff'}} />
    </AbsoluteFill>
  );
};
