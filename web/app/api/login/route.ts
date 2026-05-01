import { createHash } from 'crypto'
import { NextResponse } from 'next/server'

const PASSWORD = 'vanguardcreatives'
const TOKEN = createHash('sha256').update(PASSWORD).digest('hex')

export async function POST(request: Request) {
  const { password } = await request.json()
  if (password === PASSWORD) {
    const res = NextResponse.json({ ok: true })
    res.cookies.set('vc_session', TOKEN, {
      httpOnly: true,
      path: '/',
      maxAge: 60 * 60 * 24 * 30,
      sameSite: 'strict',
    })
    return res
  }
  return NextResponse.json({ error: 'Wrong password' }, { status: 401 })
}
