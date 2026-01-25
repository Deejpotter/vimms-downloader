import { render, fireEvent, waitFor } from '@testing-library/react';
import AdminPanel from './AdminPanel';
import * as api from '../services/configApi';

jest.mock('../services/configApi');

test('loads config on open and displays folders', async () => {
  api.getConfig.mockResolvedValue({ workspace_root: 'H:/Games', folders: { DS: {active:true, priority:1}, GBA: {active: true, priority:2}}});
  const onClose = jest.fn();
  const { getByText } = render(<AdminPanel open={true} onClose={onClose} />);
  await waitFor(()=> expect(getByText('DS')).toBeTruthy());
});