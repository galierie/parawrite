import { PUBLIC_API_URL_HTTP } from '$env/static/public';
import { fail, type Actions } from '@sveltejs/kit';
import assert from 'assert';

export const actions: Actions = {
  async rate({ fetch, request }) {
    const formData = await request.formData();

    const unparsedRating = formData.get('rating') as string | null;
    assert(unparsedRating !== null);
    const rating  = parseInt(unparsedRating, 10);

    const response = await fetch(`${PUBLIC_API_URL_HTTP}/rate`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        rating,
      }),
    });

    if (!response.ok) fail(500, { message: 'Uh-oh' });

    return { success: true, message: 'Rated successfully!' };
  },
};