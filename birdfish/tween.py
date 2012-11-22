"""
Tween functions
t = current time
b = start value
c = change in value
d = total duration
"""

import math

def OUT_EXPO(t, b, c, d ):
    return b+c if (t==d) else c * (-2**(-10 * t/d) + 1) + b

def IN_EXPO(t, b, c, d):
    return b if (t==0) else c * (2**(10 * (t/d -1))) + b
    # class com.robertpenner.easing.Expo {
    #   static function easeIn (t:Number, b:Number, c:Number, d:Number):Number {
    #       return (t==0) ? b : c * Math.pow(2, 10 * (t/d - 1)) + b;
    #   }
    #   static function easeOut (t:Number, b:Number, c:Number, d:Number):Number {
    #       return (t==d) ? b+c : c * (-Math.pow(2, -10 * t/d) + 1) + b;
    #   }
    #   static function easeInOut (t:Number, b:Number, c:Number, d:Number):Number {
    #       if (t==0) return b;
    #       if (t==d) return b+c;
    #       if ((t/=d/2) < 1) return c/2 * Math.pow(2, 10 * (t - 1)) + b;
    #       return c/2 * (-Math.pow(2, -10 * --t) + 2) + b;
    #   }
    #  }

def IN_CIRC(t, b, c, d):
    #   return -c * (Math.sqrt(1 - (t/=d)*t) - 1) + b;
    t/=d
    return -c * (math.sqrt(1 - (t)*t) - 1) + b

def LINEAR (t, b, c, d):
    return c*t/d + b

def IN_QUAD (t, b, c, d):
    t/=d
    return c*(t)*t + b

def OUT_QUAD (t, b, c, d):
    t/=d
    return -c *(t)*(t-2) + b

def IN_OUT_QUAD( t, b, c, d ):
    t/=d/2
    if ((t) < 1): return c/2*t*t + b
    t-=1
    return -c/2 * ((t)*(t-2) - 1) + b

def OUT_IN_QUAD( t, b, c, d ):
    if (t < d/2):
        return OUT_QUAD (t*2, b, c/2, d)
    return IN_QUAD((t*2)-d, b+c/2, c/2, d)

def IN_CUBIC(t, b, c, d):
    t/=d
    return c*(t)*t*t + b

def OUT_CUBIC(t, b, c, d):
    t=t/d-1
    return c*((t)*t*t + 1) + b

def IN_OUT_CUBIC( t, b, c, d):
    t/=d/2
    if ((t) < 1):
         return c/2*t*t*t + b
    t-=2
    return c/2*((t)*t*t + 2) + b

def OUT_IN_CUBIC( t, b, c, d ):
    if (t < d/2): return OUT_CUBIC (t*2, b, c/2, d)
    return IN_CUBIC((t*2)-d, b+c/2, c/2, d)

def IN_QUART( t, b, c, d):
    t/=d
    return c*(t)*t*t*t + b

def OUT_QUART( t, b, c, d):
    t=t/d-1
    return -c * ((t)*t*t*t - 1) + b

def IN_OUT_QUART( t, b, c, d):
    t/=d/2
    if (t < 1):
        return c/2*t*t*t*t + b
    t-=2
    return -c/2 * ((t)*t*t*t - 2) + b

def OUT_BOUNCE(t, b, c, d):
    t/=d
    if (t < (1.0/2.75)):
        return c*(7.5625*t*t) + b
    elif (t < (2.0/2.75)):
        t-=(1.5/2.75)
        return c*(7.5625*(t)*t + .75) + b
    elif (t < (2.5/2.75)):
        t-=(2.25/2.75)
        return c*(7.5625*(t)*t + .9375) + b
    else:
        t-=(2.625/2.75)
        return c*(7.5625*(t)*t + .984375) + b

def OUT_ELASTIC(t, b, c, d):
    if (t==0):
        return b
    t/=d
    if t==1:
        return b+c
    p = period = d*.3
    a = amplitude = 1.0
    if a < abs(c):
        a = c
        s = p/4
    else:
        s = p/(2*math.pi) * math.asin (c/a)

    return (a*math.pow(2,-10*t) * math.sin( (t*d-s)*(2*math.pi)/p ) + c + b)

def IN_BACK(t, b, c, d):
    #         static function easeIn (t:Number, b:Number, c:Number, d:Number, s:Number):Number {
    #   if (s == undefined) s = 1.70158;
    #   return c*(t/=d)*t*((s+1)*t - s) + b;
    # }
    s = 1.70158
    t/=d
    return c*(t)*t*((s+1)*t - s) + b

def OUT_BACK(t, b, c, d):
    #         static function easeOut (t:Number, b:Number, c:Number, d:Number, s:Number):Number {
    #   if (s == undefined) s = 1.70158;
    #   return c*((t=t/d-1)*t*((s+1)*t + s) + 1) + b;
    # }
    s = 1.70158
    t=t/d-1
    return c*((t)*t*((s+1)*t + s) + 1) + b

def IN_OUT_BACK(t, b, c, d):
    #         static function easeInOut (t:Number, b:Number, c:Number, d:Number, s:Number):Number {
    #   if (s == undefined) s = 1.70158;
    #   if ((t/=d/2) < 1) return c/2*(t*t*(((s*=(1.525))+1)*t - s)) + b;
    #   return c/2*((t-=2)*t*(((s*=(1.525))+1)*t + s) + 2) + b;
    # }
    s = 1.70158
    t/=d/2
    if (t < 1):
        s*=(1.525)
        return c/2*(t*t*(((s+1))*t - s)) + b
    else:
        t-=2
        s*=(1.525)
        return c/2*((t)*t*(((s)+1)*t + s) + 2) + b

