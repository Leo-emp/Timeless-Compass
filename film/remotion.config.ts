// Remotion settings shared by `remotion still` (laptop self-check) and the cloud part renderer.
import { Config } from '@remotion/cli/config';

Config.setVideoImageFormat('jpeg');   // frames are flat cartoon art: jpeg frames encode fast and look the same
Config.setJpegQuality(95);            // high quality so outlines stay crisp
Config.setCodec('h264');
Config.setPixelFormat('yuv420p');     // plays everywhere (YouTube, phones)
