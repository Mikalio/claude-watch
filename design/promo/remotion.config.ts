import {Config} from '@remotion/cli/config';

Config.setChromiumOpenGlRenderer('angle'); // the graphics card, not software
Config.setConcurrency(4);
if (!process.env.AUDIO_ONLY) { // none of these apply when rendering just the sound
  Config.setVideoImageFormat('jpeg');
  Config.setJpegQuality(96);
  Config.setCrf(18);
  Config.setPixelFormat('yuv420p');
  Config.setColorSpace('bt709');
}
