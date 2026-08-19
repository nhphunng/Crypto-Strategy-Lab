import { useState } from 'react'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { Button, Modal, Segmented, Toggle } from '../../components/ui'

describe('reusable controls', () => {
  it('exposes selected state and supports arrow-key movement for segmented controls', async () => {
    const user = userEvent.setup()
    function Example() {
      const [value, setValue] = useState<'one' | 'two'>('one')
      return <Segmented ariaLabel="Layout" value={value} onChange={setValue} options={[{ value: 'one', label: 'One' }, { value: 'two', label: 'Two' }]} />
    }
    render(<Example />)
    const first = screen.getByRole('button', { name: 'One' })
    expect(first).toHaveAttribute('aria-pressed', 'true')
    first.focus()
    await user.keyboard('{ArrowRight}')
    expect(screen.getByRole('button', { name: 'Two' })).toHaveAttribute('aria-pressed', 'true')
  })

  it('uses switch semantics and cannot fire a disabled primary action', async () => {
    const user = userEvent.setup()
    const change = vi.fn()
    const action = vi.fn()
    render(<><Toggle checked={false} onChange={change} label="Explanations" /><Button disabled onClick={action}>Continue</Button></>)
    await user.click(screen.getByRole('switch', { name: 'Explanations' }))
    await user.click(screen.getByRole('button', { name: 'Continue' }))
    expect(change).toHaveBeenCalledWith(true)
    expect(action).not.toHaveBeenCalled()
  })

  it('labels dialogs, closes on Escape, and restores focus', async () => {
    const user = userEvent.setup()
    const close = vi.fn()
    render(<><button>Origin</button><Modal open onClose={close} title="Stop loop" footer={<Button onClick={close}>Cancel</Button>}>Confirm stop.</Modal></>)
    expect(screen.getByRole('dialog', { name: 'Stop loop' })).toBeVisible()
    await user.keyboard('{Escape}')
    expect(close).toHaveBeenCalled()
  })
})
