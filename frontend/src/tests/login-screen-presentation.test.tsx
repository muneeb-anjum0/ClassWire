import { act, render, screen } from '@testing-library/react';
import { vi } from 'vitest';
import LoginScreen from '../components/LoginScreen/LoginScreen';
import { BACKEND_WAKE_EVENT } from '../services/api';

vi.mock('../context/AuthContext', () => ({
  useAuth: () => ({
    loginWithGmail: vi.fn(),
    authenticationError: '',
  }),
}));

test('login screen uses the SZABIST access band and amber backend wake treatment', () => {
  const { container } = render(<LoginScreen />);

  expect(screen.getByText('Read-only Gmail')).toBeInTheDocument();
  expect(screen.getByText('SZABIST Islamabad')).toBeInTheDocument();
  expect(container.querySelector('.login-card__signal')).toBeInTheDocument();

  act(() => {
    window.dispatchEvent(new CustomEvent(BACKEND_WAKE_EVENT, {
      detail: { active: true, message: 'Render is waking up.' },
    }));
  });

  expect(screen.getByText('Render is waking up.').closest('.status-box')).toHaveClass('status-box--wake');
});
