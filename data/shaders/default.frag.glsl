#version 130

const int SHADOW_MAP_CASCADE_COUNT = 5;

in vec3 view_pos;
in vec3 view_normal;
in vec3 view_light_dir;
in vec4 light_frag_pos[SHADOW_MAP_CASCADE_COUNT];

out vec4 frag_color;

uniform vec3 object_color = vec3(0.5, 0.5, 0.5);
uniform vec3 light_color = vec3(1.0, 1.0, 1.0);
uniform sampler2DArray shadow_map;
uniform vec4 cascade_far_splits;

const vec3 view_camera_dir = vec3(0.0, 0.0, 1.0);

float computeShadowFactor(vec4 light_frag_pos, int cascade_idx) {
  vec3 proj_light_frag_pos = light_frag_pos.xyz / light_frag_pos.w;
  vec3 shadow_map_coords = vec3(0.5 * proj_light_frag_pos.xy + 0.5,
                                cascade_idx);
  float frag_depth = 0.5 * proj_light_frag_pos.z + 0.5;
  float shadow_map_depth = texture(shadow_map, shadow_map_coords).r;
  if (frag_depth <= shadow_map_depth) {
    // Fragment is closer to the light than the shadow map depth
    return 1.0;
  } else {
    return 0.0;
  }
}

void main() {
  vec3 normal = normalize(view_normal);
  vec3 reflect_dir = reflect(-view_light_dir, normal);
  int cascade_idx = int(dot(
      vec4(greaterThan(-view_pos.zzzz, cascade_far_splits)), vec4(1.0)));
  float shadow_factor = computeShadowFactor(
      light_frag_pos[cascade_idx], cascade_idx);

  vec3 ambient = 0.1 * light_color;
  vec3 diffuse = max(dot(normal, view_light_dir), 0.0) * light_color *
                 shadow_factor;
  float spec_factor = pow(max(dot(view_camera_dir, reflect_dir), 0.0), 32);
  vec3 specular = 0.5 * spec_factor * light_color * shadow_factor;

  frag_color = vec4((ambient + diffuse + specular) * object_color, 1.0);
}